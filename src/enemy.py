#from direct.showbase.DirectObject import DirectObject
from panda3d.core import *
from direct.actor.Actor import Actor
from direct.fsm.FSM import FSM
from panda3d.ai import *
from direct.interval.IntervalGlobal import *

from collections import namedtuple

import utils
from unit import Unit

Attributes = namedtuple('Attributes', ['strength', 'constitution', 'dexterity', 'expAward', 'perceptionRange', 'combatRange', 'movementSpeed', 'mass', 'initiativeBonus', 'fixedHealthPoints', 'armorClass', 'startLevel', 'damageBonus', 'damageRange', 'attackBonus'])

# Kobold Minion uses fixedHealthPoints, which given any other value than 0 will fix the units health to that value
# Mass should be thought of as approximate weight in kilograms
koboldMinion = Attributes(strength=8, constitution=12, dexterity=16, initiativeBonus=3, fixedHealthPoints=1, armorClass=15, movementSpeed=6, perceptionRange=2, combatRange=1, mass=60, expAward=25, startLevel=1, damageRange=0, damageBonus=4, attackBonus=5)

# Kobold Skirmisher has combatRange of 1, means very short range (melee)
# Perception +1 bonus gives perception range 2
koboldSkirmisher = Attributes(strength=8, constitution=11, dexterity=16, initiativeBonus=5, fixedHealthPoints=27, armorClass=15, movementSpeed=6, perceptionRange=1, combatRange=1, mass=60, expAward=100, startLevel=1, damageRange=8, damageBonus=0, attackBonus=6)

# Kobold Slinger has combat range 3 (ranged), which means that perception +1 gives perception range 4
# Damage bonus 3 gives constant +3 to damage, while damage range 4 means 1d4 (1-4)
koboldSlinger = Attributes(strength=9, constitution=12, dexterity=17, fixedHealthPoints=24, initiativeBonus=3, perceptionRange=4, combatRange=3, movementSpeed=6, armorClass=13, mass=60, expAward=100, startLevel=2, damageBonus=3, damageRange=4, attackBonus=5)

# Enemy unit automatically levels up to startLevel
koboldWyrmpriest = Attributes(strength=9, constitution=12, dexterity=16, initiativeBonus=4, fixedHealthPoints=36, armorClass=17, movementSpeed=6, combatRange=1, perceptionRange=5, mass=70, expAward=150, startLevel=3, damageRange=8, damageBonus=0, attackBonus=7)

class Enemy(FSM, Unit):

    # Declare private variables
    _removeCorpseDelay = 3 # seconds before corpse is cleaned

    def __init__(self, mainRef, modelName, attributes):
        print("Enemy class instantiated")
        Unit.__init__(self)
        FSM.__init__(self, 'playerFSM')

        self._enemyListRef = mainRef.enemyList
        self._AIworldRef = mainRef.AIworld
        self._playerRef = mainRef.player
        self._worldRef = mainRef
        self._modelName = modelName

        self.topEnemyNode = mainRef.mainNode.attachNewNode('topEnemyNode')

        enemyName = 'enemy' + str(len(self._enemyListRef))
        self.enemyNode = self.topEnemyNode.attachNewNode(enemyName)
        self._enemyListRef.append(self.enemyNode)

        utils.enemyDictionary[self.enemyNode.getName()] = self

        self.loadEnemyModel()
        self.initAttributes(attributes)
        self.initEnemyAi()
        
        self.initEnemyCollisionHandlers()
        self.initEnemyCollisionSolids()

        self.targeted = False

    def loadEnemyModel(self):
        self.enemyModel = Actor('models/' + self._modelName + '.egg')
        self.enemyModel.reparentTo(self.enemyNode)

        self.enemyNode.setPos(-2, 0, 1)
        self.enemyNode.setScale(0.1)

    def initAttributes(self, attributes):
        self.strength = attributes.strength
        self.constitution = attributes.constitution
        self.dexterity = attributes.dexterity

        self.mass = attributes.mass
        self.movementSpeed = attributes.movementSpeed
        self.perceptionRange = attributes.perceptionRange
        self.combatRange = attributes.combatRange
        self.attackBonus = attributes.attackBonus
        self.damageBonus = attributes.damageBonus
        self.damageRange = attributes.damageRange
        self.initiativeBonus = attributes.initiativeBonus
        self.fixedHealthPoints = attributes.fixedHealthPoints
        self.armorClass = attributes.armorClass

        if attributes.startLevel > 1:
            for i in range(attributes.startLevel-1):
                enemy.increaseLevel()

        self.expAward = attributes.expAward

        self.initHealth()

    def initEnemyAi(self):
        self.enemyAI = AICharacter('enemy',
                                self.enemyNode,
                                self.mass, # Mass
                                0.1, # Movt force
                                self.movementSpeed) # Max force
        self._AIworldRef.addAiChar(self.enemyAI)

        self.enemyAIBehaviors = self.enemyAI.getAiBehaviors()
        #self.enemyAIBehaviors.obstacleAvoidance(1.0)

        enemyUpdateTask = taskMgr.add(self.enemyUpdater, 'enemyUpdaterTask')
        enemyUpdateTask.last = 0

        self.request('Idle')

    def enemyUpdater(self, task):
        deltaTime = task.time - task.last
        task.last = task.time

        #if deltaTime < .2:
        #    return task.cont
        self.checkGroundCollisions()

        #print('enemyUpdater')
        if self.state == 'Death':
            return task.done

        if self._playerRef.getIsDead():
            return task.cont

        playerPos = self._playerRef.playerNode.getPos()
        enemyPos = self.enemyNode.getPos()

        # If player is within enemy perception range
        if utils.getIsInRange(playerPos, enemyPos, self.perceptionRange):
            #print('player in range')
            # If enemy is not doing anything
            if self.state == 'Idle':
                # Start pursuing
                self.request('Pursue')

            # If enemy is already pursueing
            elif self.state == 'Pursue':
                # If player is within combat range
                if utils.getIsInRange(playerPos, enemyPos, self.combatRange):
                    # Go to combat
                    self.request('Combat')

            # If already in combat, attack!
            elif self.state == 'Combat':
                pass # Combat is now handled in attackPlayer method and enterCombat
                #print('in combat')
        # If player is not within perception range
        else:
            # if in combat
            if self.state == 'Combat':
                pass # Combat is now handled in attackPlayer method and enterCombat

            elif self.state != 'Idle':
                self.request('Idle')

        return task.cont

    def enterPursue(self):
        print('enterPursue')
        self.enemyAIBehaviors.pursue(self._playerRef.playerNode)

    def exitPursue(self):
        print('exitPursue')
        #self.enemyAIBehaviors.removeAi('pursue')

    def enterCombat(self):
        print('enterCombat')
        delay = Wait(1.5)
        
        attackSequence = Sequence()

        attackPlayer = Func(self.attackPlayer, attackSequence)
        attackEnemy = Func(self._playerRef.attackEnemy, self)

        if self.getInitiativeRoll() > self._playerRef.getInitiativeRoll():
            # Enemy wins initiative roll
            attackSequence.append(attackPlayer)
            attackSequence.append(delay)
            attackSequence.append(attackEnemy)
            attackSequence.append(delay)
        else:
            # Player wins initiative roll
            attackSequence.append(attackEnemy)
            attackSequence.append(delay)
            attackSequence.append(attackPlayer)
            attackSequence.append(delay)

        attackSequence.loop()

    def exitCombat(self):
        print('exitCombat')

    def enterDeath(self):
        print('enterDeath')
        self.enemyAIBehaviors.removeAi('all')

    def enterIdle(self):
        print('enterIdle')
        self.enemyAIBehaviors.removeAi('pursue')
        self.enemyAIBehaviors.wander(2.5, 0, 5)

    def exitIdle(self):
        print('exitIdle')
        self.enemyAIBehaviors.removeAi('wander')

    def attackPlayer(self, attackSequence):
        playerPos = self._playerRef.playerNode.getPos()
        enemyPos = self.enemyNode.getPos()

        if self.getIsDead():
            print('enemy is already dead')
            self.onDeath()
            attackSequence.finish()

        elif self._playerRef.getIsDead():
            print('player is already dead')
            self.request('Idle')
            attackSequence.finish()

        elif utils.getIsInRange(playerPos, enemyPos, self.combatRange) == False:
            print('player fled away from combat range')
            self.request('Pursue')
            attackSequence.finish()

        elif utils.getIsInRange(playerPos, enemyPos, self.perceptionRange) == False:
            print('player fled away from perception range')
            self.request('Idle')
            attackSequence.finish()

        else:
            # Play attack animation
            print('Attack player!')
            if self._playerRef.getArmorClass() <= self.getAttackBonus():
                dmg = self.getDamageBonus()
                print('Enemy hit the player for ' + str(dmg) + ' damage')
                self._playerRef.receiveDamage(dmg)
            else:
                print('Enemy missed the player')

    def onDeath(self):
        if self.getIsDead():
            # Award the player exp
            self._playerRef.receiveEXP(self.expAward)

            # Change state
            self.request('Death')

            # Remove enemy
            taskMgr.doMethodLater(self._removeCorpseDelay,
                             self.removeCorpse,
                            'RemoveCorpseTask')

    def removeCorpse(self, task):
        # Remove enemy from enemyList
        self._enemyListRef.remove(self.enemyNode)

        # Cleanup the enemy model
        self.enemyModel.cleanup()
        self.enemyModel.delete()

        # Cleanup FSM
        self.cleanup()

        # Remove the enemy node
        self.enemyNode.removeNode()
        self.topEnemyNode.removeNode()

        return task.done

    def getEnemyNode(self):
        return self.enemyNode

    def moveEnemy(self, x, y):
        self.enemyNode.setPos(x, y, 10)

    def initEnemyCollisionHandlers(self):
        self.groundHandler = CollisionHandlerQueue()

    def initEnemyCollisionSolids(self):
        sphereCollNode = CollisionNode(self.enemyNode.getName())
        sphereNodePath = self.enemyNode.attachNewNode(sphereCollNode)
        collSphere = CollisionSphere(0, 0, 0, 15)
        sphereCollNode.addSolid(collSphere)
        #self.sphereCollNode.show()

        groundRay = CollisionRay(0, 0, 10, 0, 0, -1)
        groundColl = CollisionNode('groundRay')
        groundColl.addSolid(groundRay)
        groundColl.setIntoCollideMask(BitMask32.allOff())
        groundColl.setFromCollideMask(BitMask32.bit(1))
        self.groundRayNode = self.topEnemyNode.attachNewNode(groundColl)
        #self.groundRayNode.show()

        base.cTrav.addCollider(self.groundRayNode, self.groundHandler)

    def checkGroundCollisions(self):
        zModifier = 0.5

        if self.groundHandler.getNumEntries() > 0:
            self.groundHandler.sortEntries()
            entries = []
            for i in range(self.groundHandler.getNumEntries()):
                entry = self.groundHandler.getEntry(i)
                entries.append(entry)

            entries.sort(lambda x,y: cmp(y.getSurfacePoint(render).getZ(),
                                        x.getSurfacePoint(render).getZ()))

            if (len(entries) > 0) and (entries[0].getIntoNode().getName() == 'groundcnode'):
                newZ = entries[0].getSurfacePoint(base.render).getZ()
                self.enemyNode.setZ(zModifier + newZ)