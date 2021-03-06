from direct.showbase.DirectObject import DirectObject
from panda3d.core import *
from direct.actor.Actor import Actor
from direct.fsm.FSM import FSM
from direct.interval.IntervalGlobal import *

import utils
from unit import Unit

class Player(FSM, Unit):

    # Declare private variables
    _cameraYModifier = -6 # Relative to player Y position
    _cameraZModifier = 4.5 # Relative to player Z position

    _currentTarget = None

#------------------- CONSTRUCTOR ----------------------#
    def __init__(self, mainRef):
        print("Player instantiated")
        Unit.__init__(self)
        FSM.__init__(self, 'playerFSM')

        self._hudRef = None
        self._mainRef = mainRef
        self._enemyListRef = mainRef.enemyList
        self._ddaHandlerRef = mainRef.DDAHandler
        self._mapHandlerRef = mainRef.mapHandler
        self._stateHandlerRef = mainRef.stateHandler
        self._scenarioHandlerRef = mainRef.scenarioHandler

        self.playerNode = mainRef.mainNode.attachNewNode('playerNode')

        self.initPlayerAttributes()
        self.initPlayerModel()
        self.initPlayerCamera()
        self.initPlayerAbilities()

        self.initPlayerCollisionHandlers()
        self.initPlayerCollisionSolids()

        self.initPlayerDDA()

        # Start mouse picking and movement
        self.mouseHandler = utils.MouseHandler(self)

        # Start player update task
        playerUpdateTask = taskMgr.add(self.playerUpdate, 'playerUpdateTask')

        # Initialize player FSM state
        self.request('Idle')

        DO = DirectObject()
        DO.accept('shift-mouse1', self.onShiftDown)
        DO.accept('shift-up', self.onShiftUp)

        self._shiftButtonDown = False

    def onShiftDown(self):
        self._shiftButtonDown = True

        attackDelay = self.getInitiativeRoll()
        taskMgr.doMethodLater(attackDelay, self.shiftAttack, 'shiftAttackTask')

    def onShiftUp(self):
        self._shiftButtonDown = False

        taskMgr.remove('shiftAttackTask')

#----------------------------- INITIALIZATION ---------------------------------#
    def initPlayerAttributes(self):
        # Initialize player attributes
        self.strength = 16
        self.constitution = 14
        self.dexterity = 10

        self.combatRange = 0.75 # Melee
        self.movementSpeed = 1 # ?
        self.attackBonus = 6 # ?
        self.damageBonus = 0 # ?
        self.damageRange = 8 # = Longsword
        self.initiativeBonus = 1 # ?
        self.armorClass = 10 + 8 # Base armor class + fullplate armor
        self.mass = 90

        self.startLevel = 3

        for i in range(1, self.startLevel):
            self.increaseLevel()

        self.initHealth()

        # Used by area transition system
        self.areaTransitioning = False

    def initPlayerModel(self):
        # Initialize the player model (Actor)
        modelPrefix = 'models/player-'
        self.playerModel = Actor(modelPrefix + 'model', {
            'run':modelPrefix+'run',
            'attack':modelPrefix+'attack',
            'stop':modelPrefix+'stop',
            'hit':modelPrefix+'hit',
            'defense':modelPrefix+'defense',
            'death':modelPrefix+'death',
            'idle':modelPrefix+'idle',
            'bull-rush':modelPrefix+'bull-rush',
            'thicket-blades':modelPrefix+'thicket-blades',
            'level-up':modelPrefix+'level-up'
            })

        self.playerModel.reparentTo(self.playerNode)

        # Make sure that visible geometry does not collide
        self.playerModel.setCollideMask(BitMask32.allOff())
        # Model is backwards, fix by changing the heading
        self.playerModel.setH(180)

    def initPlayerCamera(self): 
        # Initialize the camera
        base.disableMouse()

        base.camera.setPos(self.playerNode, (0, self._cameraYModifier, self._cameraZModifier))
        base.camera.lookAt(self.playerNode)

        self.stopCamera = False

    def initStartPosition(self, playerStartPos, playerExitPos):
        self.exitPos = playerExitPos
        self.startPos = playerStartPos

        self.initPlayerMovement()

    def initPlayerMovement(self):
        # Make sure the player starts at the starting position
        self.playerNode.setPos(self.startPos)
        self.destination = Point3(self.startPos)
        self.velocity = Vec3.zero()

        self.playerNode.headsUp(self.exitPos)

    def initPlayerAbilities(self):
        DO = DirectObject()
        DO.accept('1', self.fireAbility, [1])
        DO.accept('2', self.fireAbility, [2])
        DO.accept('3', self.fireAbility, [3])
        DO.accept('4', self.fireAbility, [4])

        self.abilityDict = {'offensive':1, 'defensive':1, 'evasive':1, 'area':1}

    def initPlayerDDA(self):
        if self._scenarioHandlerRef.getHasDDA():
            self.damageHistory = []
            self.healthHistory = []
            self.deathHistory = []

            self.damageReceived = 0
            self.deathCount = 0

            self._ddaHandlerRef.initPlayerDDA(self)

            ddaMonitorTask = taskMgr.doMethodLater(1, self.ddaMonitor, 'ddaMonitorTask')
            ddaMonitorTask.count = 0

#-------------------- COLLISION INITIALIZATION ---------------------------#
    def initPlayerCollisionHandlers(self):
        self.groundHandler = CollisionHandlerQueue()
        self.collPusher = CollisionHandlerPusher()
        self.attackCollisionHandler = CollisionHandlerQueue()
        self.cameraGroundHandler = CollisionHandlerQueue()

    def initPlayerCollisionSolids(self):
        # Player ground ray #
        groundRay = CollisionRay(0, 0, 1, 0, 0, -1)
        groundColl = CollisionNode('playerGroundRay')

        groundColl.addSolid(groundRay)
        groundColl.setIntoCollideMask(BitMask32.allOff())
        groundColl.setFromCollideMask(BitMask32.bit(1))
        self.groundRayNode = self.playerNode.attachNewNode(groundColl)
        #self.groundRayNode.show()

        base.cTrav.addCollider(self.groundRayNode, self.groundHandler)

        # Player collision sphere #
        collSphereNode = CollisionNode('playerCollSphere')

        collSphere = CollisionSphere(0, 0, 0.1, 0.2)
        collSphereNode.addSolid(collSphere)

        #collSphereNode.setCollideMask(BitMask32.bit(2))
        collSphereNode.setIntoCollideMask(BitMask32.allOff())
        collSphereNode.setFromCollideMask(BitMask32.bit(2))
        
        sphereNode = self.playerNode.attachNewNode(collSphereNode)
        #sphereNode.show()

        base.cTrav.addCollider(sphereNode, self.collPusher)
        self.collPusher.addCollider(sphereNode, self.playerNode)

        # Player attack collision sphere # 
        attackCollSphereNode = CollisionNode('playerAttackCollSphere')

        attackCollSphere = CollisionSphere(0, 0.3, 0.1, 0.2)
        attackCollSphereNode.addSolid(attackCollSphere)

        attackCollSphereNode.setIntoCollideMask(BitMask32.allOff())
        attackCollSphereNode.setFromCollideMask(BitMask32.bit(3))

        attackSphereNode = self.playerNode.attachNewNode(attackCollSphereNode)
        #attackSphereNode.show()

        base.cTrav.addCollider(attackSphereNode, self.attackCollisionHandler)

#---------------------------- EXPERIENCE ----------------------------------------#
    def getEXPToNextLevel(self):
        return self._prevEXP + (self.level * 1000)

    def receiveEXP(self, value):
        expGain = value * self._ddaHandlerRef.EXPFactor
        self.experience += expGain
        self._hudRef.printFeedback('Experience gained: ' + str(int(expGain)), False)

        if self.experience >= self.getEXPToNextLevel():
            self.increaseLevel()
            self._hudRef.printFeedback('Level gained!', False)
            self.playerModel.play('level-up', fromFrame=0, toFrame=25)

    def getEXPToNextLevelInPercentage(self):
        currentEXP = self.experience - self._prevEXP
        expToNextLevel = self.level * 1000.0

        result = int(currentEXP / expToNextLevel * 100.0)

        return result

#-------------------------- PLAYER MOVEMENT -------------------------------------#
    def setPlayerDestination(self, destination):
        if self._stateHandlerRef.state != self._stateHandlerRef.PLAY:
            # Do not do anything when paused
            return 

        if self.getIsDead():
            return

        pitchRoll = self.playerNode.getP(), self.playerNode.getR()
        self.playerNode.headsUp(destination)
        self.playerNode.setHpr(self.playerNode.getH(), *pitchRoll)

        distance = abs(self.playerNode.getX() - destination.getX()) + abs(self.playerNode.getY() - destination.getY())
        if distance > .5:
            self.destination = destination
            self.velocity = self.destination - self.playerNode.getPos()

            self.velocity.normalize()
            self.velocity *= self.movementSpeed

#-------------------- PLAYER TARGET ------------------------------------#
    def setCurrentTarget(self, target):
        self._currentTarget = target

    def getCurrentTarget(self):
        return self._currentTarget

    def removeCurrentTarget(self):
        self.setCurrentTarget(None)

#-------------------- PLAYER ABILITIES ----------------------------------#
    def startCooldown(self, ability, cooldown, task):
        task.count += 1

        if task.count >= cooldown:
            self.abilityDict[ability] = 1
            if ability == 'offensive':
                self._hudRef.activateIcon(1)
            elif ability == 'defensive':
                self._hudRef.activateIcon(2)
            elif ability == 'evasive':
                self._hudRef.activateIcon(3)
            elif ability == 'area':
                self._hudRef.activateIcon(4)
            return task.done
        else:
            return task.again

    def fireAbility(self, ability):
        if self._stateHandlerRef.state != self._stateHandlerRef.PLAY:
            # Do not do anything when paused
            return 

        self.playerModel.stop()

        # Offensive ability - Bull Rush 10 sec cd
        if ability == 1:
            off = 'offensive'
            if self.abilityDict[off] == 1:
                if self.bullRush():
                    self.abilityDict[off] = 0
                    cd = taskMgr.doMethodLater(1, self.startCooldown, 'startCooldownTask', extraArgs=[off, 10], appendTask=True)
                    cd.count = 0

                    self._hudRef.deactivateIcon(1)
                    self.playerModel.play('bull-rush', fromFrame=0, toFrame=25)
            else:
                #print 'Bull Rush in cd'
                self._hudRef.printFeedback('Bull Rush is in cooldown')

        # Defensive - Unstoppable 10 sec cd
        elif ability == 2:
            defe = 'defensive'
            if self.abilityDict[defe] == 1:
                if self.unstoppable():
                    self.abilityDict[defe] = 0
                    cd = taskMgr.doMethodLater(1, self.startCooldown, 'startCooldownTask', extraArgs=[defe, 10], appendTask=True)
                    cd.count = 0

                    self._hudRef.deactivateIcon(2)
                    self.playerModel.play('defense', fromFrame=0, toFrame=12)
            else:
                #print 'Unstoppable in cd'
                self._hudRef.printFeedback('Unstoppable is in cooldown')

        # Evasive - Thicket of Blades 20 sec cd
        elif ability == 3:
            eva = 'evasive'
            if self.abilityDict[eva] == 1:
                if self.thicketOfBlades():
                    self.abilityDict[eva] = 0
                    cd = taskMgr.doMethodLater(1, self.startCooldown, 'startCooldownTask', extraArgs=[eva, 20], appendTask=True)
                    cd.count = 0

                    self._hudRef.deactivateIcon(3)
                    self.playerModel.play('thicket-blades', fromFrame=0, toFrame=27)
            else:
                #print 'Thicket of Blades in cd'
                self._hudRef.printFeedback('Thicket of Blades is in cooldown')

        # Area of Effect - Shift the Battlefield 30 sec cd
        elif ability == 4:
            aoe = 'area'
            if self.abilityDict[aoe] == 1:
                if self.shiftTheBattlefield():
                    self.abilityDict[aoe] = 0
                    cd = taskMgr.doMethodLater(1, self.startCooldown, 'startCooldownTask', extraArgs=[aoe, 30], appendTask=True)
                    cd.count = 0

                    self._hudRef.deactivateIcon(4)
            else:
                #print 'Shift the Battlefield in cd'
                self._hudRef.printFeedback('Shift the Battlefield is in cooldown')

    def bullRush(self):
        bSuccess = False

        enemy = self.getCurrentTarget()
        if enemy is not None and not enemy.getIsDead():
            if self.state == 'Combat':
                node = enemy.enemyNode
                print 'Bull rush:', node
                bSuccess = True

                if self.getStrengthModifier() + utils.getD20() > enemy.armorClass:
                    self._hudRef.printFeedback('Bull Rush hit', True)
                    self.enemyFleeFromPlayer(enemy)

                    self.playerModel.play('attack')
                    enemy.playHitAnimation()
                else:
                    #print 'bullRush missed'
                    self._hudRef.printFeedback('Bull Rush missed')

        return bSuccess

    def unstoppable(self):
        tempHp = utils.getD6() + utils.getD6() + self.getConstitutionModifier()
        self.receiveTemporaryHealth(tempHp)
        print 'unstoppable:', tempHp

        taskMgr.doMethodLater(1.5, self.stopDefenseAnimation, 'stopDefenseAnimationTask')

        self._hudRef.printFeedback('Unstoppable activated', False)

        duration = 30.0 # Half a minute (30 seconds) duration of temp hp
        taskMgr.doMethodLater(duration, self.removeTempHp, 'removeTempHpTask')

        return True

    def stopDefenseAnimation(self, task):
        #print('stop defense animation')
        self.playerModel.loop('idle')

        return task.done

    def removeTempHp(self, task):
        print 'removeTempHp'
        self.removeTemporaryHealth()
        return task.done

    def thicketOfBlades(self):
        bSuccess = False

        numEntries = self.attackCollisionHandler.getNumEntries()
        if numEntries > 0:
            self.attackCollisionHandler.sortEntries()

            for i in range(numEntries):
                entry = self.attackCollisionHandler.getEntry(i).getIntoNode()
                entryName = entry.getName()[:-6]
                #print('entryFound:', entryName)

                enemy = utils.enemyDictionary[entryName]
                if enemy is not None and not enemy.getIsDead():
                    if utils.getIsInRange(self.playerNode.getPos(), enemy.enemyNode.getPos(), self.combatRange):
                        bSuccess  = True
                        if self.getStrengthModifier() + utils.getD20() > enemy.armorClass:
                            self._hudRef.printFeedback('Thicket of Blades hit', True)
                            enemy.slowMovementByPercentage(50, 10) # slow by 50 % in 10 seconds, automatically removes it again
                            enemy.enemyModel.play('hit')
                        else:
                            #print 'thicketOfBlades missed'
                            self._hudRef.printFeedback('Thicket of Blades missed')

        return bSuccess

    def shiftTheBattlefield(self):
        bSuccess = False

        playerPos = self.playerNode.getPos()
        for enemy in self._enemyListRef:
            enemyPos = enemy.enemyNode.getPos()
            if utils.getIsInRange(playerPos, enemyPos, self.combatRange):
                bSuccess = True
                if self.getStrengthModifier() + utils.getD20() > enemy.armorClass:
                    self._hudRef.printFeedback('Shift the Battlefield hit', True)
                    self.enemyFleeFromPlayer(enemy)
    
                    # Might want to replace the getD8 to depend on the player's weapon
                    dmg = 2 * utils.getD8() + self.getStrengthModifier()
                    enemy.receiveDamage(dmg)

                    enemy.enemyModel.play('hit')
                else:
                    #print 'shiftTheBattlefield missed'
                    self._hudRef.printFeedback('Shift the Battlefield missed')
                    dmg = (2 * utils.getD8() + self.getStrengthModifier()) / 2
                    enemy.receiveDamage(dmg)

                    enemy.enemyModel.play('hit')

        return bSuccess

    def enemyFleeFromPlayer(self, enemy):
        if enemy.state != 'Disabled':
            #print 'enemyFleeFromPlayer:', enemy
            enemy.enemyAIBehaviors.removeAi('all')
            enemy.enemyAIBehaviors.flee(self.playerNode)

            enemy.enemyModel.loop('walk', fromFrame=0, toFrame=12)
            enemy.request('Disabled')

            taskMgr.doMethodLater(1.5, self.removeEnemyFlee, 'removeEnemyFleeTask', extraArgs=[enemy], appendTask=True)

    def removeEnemyFlee(self, enemy, task):
        if enemy.state == 'Disabled':
            #print 'removeEnemyFlee'
            enemy.enemyModel.stop()
            enemy.enemyAIBehaviors.removeAi('flee')
            enemy.request('Idle')
        return task.done

#------------------ UPDATE FUNCTIONS ---------------------------------#
    def checkGroundCollisions(self):
        numEntries = self.groundHandler.getNumEntries()
        if numEntries > 0:
            self.groundHandler.sortEntries()
            entries = []
            for i in range(numEntries):
                entry = self.groundHandler.getEntry(i)
                entries.append(entry)

            entries.sort(lambda x,y: cmp(y.getSurfacePoint(render).getZ(),
                                         x.getSurfacePoint(render).getZ()))

            for i in range(numEntries):
                entry = entries[i]
                if entry.getIntoNode().getName()[:6] == 'ground':
                    newZ = entry.getSurfacePoint(base.render).getZ()
                    self.playerNode.setZ(newZ)
                    break;

    def updateCameraPosition(self):
        pos = self.playerNode.getPos()
        base.camera.setPos(pos.getX(), pos.getY() + self._cameraYModifier, pos.getZ() + self._cameraZModifier)

    def updatePlayerPosition(self, deltaTime):
        if not self._shiftButtonDown:
            #print('updatePlayerPosition')
            newX = self.playerNode.getX() + self.velocity.getX() * deltaTime
            newY = self.playerNode.getY() + self.velocity.getY() * deltaTime
            newZ = self.playerNode.getZ()

            self.playerNode.setFluidPos(newX, newY, newZ)

            self.velocity = self.destination - self.playerNode.getPos()
            #print('distance to dest: ', self.velocity.lengthSquared())

            if self.velocity.lengthSquared() < .2:
                self.velocity = Vec3.zero()

                if self.state == 'Run':
                    self.request('Idle')
            else:
                self.velocity.normalize()
                self.velocity *= self.movementSpeed

                if self.state != 'Run':
                    self.request('Run')
        else:
            self.destination = self.playerNode.getPos()

    def playerUpdate(self, task):
        if self._stateHandlerRef.state != self._stateHandlerRef.PLAY:
            # Do not do anything when paused
            return task.cont

        if self._hudRef == None:
            self._hudRef = self._mainRef.hud

        self.checkGroundCollisions()
        self.updateCameraPosition()

        if self.getIsDead():
            if self.state != 'Death':
                self.request('Death')

            return task.cont

        self.updatePlayerPosition(globalClock.getDt())

        return task.cont

    def ddaMonitor(self, task):
        task.count += 1
        self.healthHistory.append(self.currentHealthPoints)
        self.damageHistory.append(self.damageReceived)
        self.damageReceived = 0

        #print self.healthHistory
        #print self.damageHistory

        if (task.count + 1) % 60 == 0:
            self.deathHistory.append(self.deathCount)
            self.deathCount = 0

            print self.deathHistory

        return task.again

    def receiveDamage(self, damageAmount):
        super(Player, self).receiveDamage(damageAmount)
        if self._scenarioHandlerRef.getHasDDA():
            self.damageReceived += damageAmount

#------------------------------- COMBAT ------------------------------#
    def shiftAttack(self, task):
        if self._stateHandlerRef.state != self._stateHandlerRef.PLAY:
            return task.done

        #print 'shiftAttack. shift:', self._shiftButtonDown

        if self._shiftButtonDown and base.mouseWatcherNode.hasMouse(): 
            #print 'attack!'
            self.playerModel.play('attack')

            self.plane = Plane(Vec3(0, 0, 1), Point3(0, 0, 0))
            mousePos = base.mouseWatcherNode.getMouse()

            pos3d = Point3()
            nearPoint = Point3()
            farPoint = Point3()

            base.camLens.extrude(mousePos, nearPoint, farPoint)
            if self.plane.intersectsLine(pos3d, 
                        base.render.getRelativePoint(camera, nearPoint),
                        base.render.getRelativePoint(camera, farPoint)):
                #print('Mouse ray intersects ground at ', pos3d)
                destination = pos3d

            pitchRoll = self.playerNode.getP(), self.playerNode.getR()
            self.playerNode.headsUp(destination)
            self.playerNode.setHpr(self.playerNode.getH(), *pitchRoll)

            numEntries = self.attackCollisionHandler.getNumEntries()
            if numEntries > 0:
                self.attackCollisionHandler.sortEntries()
                bAttacked = 0

                for i in range(numEntries):
                    entry = self.attackCollisionHandler.getEntry(i).getIntoNode()
                    entryName = entry.getName()[:-6]
                    #print('entryFound:', entryName)

                    enemy = utils.enemyDictionary[entryName]
                    if enemy is not None and not enemy.getIsDead():
                        if utils.getIsInRange(self.playerNode.getPos(), enemy.enemyNode.getPos(), self.combatRange):
                            bAttacked = self.attack(enemy) # Returns 1 if player attacked but did not hit, returns 2 on hit

                if bAttacked != 0:
                    #print('attackEnemies')

                    for i in range(numEntries):
                        enemyTargetName = self.attackCollisionHandler.getEntry(i).getIntoNode().getName()[:-6]
                        enemyTarget = utils.enemyDictionary[enemyTargetName]

                        if enemyTarget is not None and not enemyTarget.getIsDead():
                            self.setCurrentTarget(enemyTarget)
                            break;
            
            return task.again
        else:
            self.playerModel.stop()

            return task.done

    def attackEnemies(self, task):
        if self._stateHandlerRef.state != self._stateHandlerRef.PLAY:
            return task.done

        if self._shiftButtonDown:
            return task.again

        numEntries = self.attackCollisionHandler.getNumEntries()
        if numEntries > 0:
            self.attackCollisionHandler.sortEntries()
            bAttacked = 0

            for i in range(numEntries):
                entry = self.attackCollisionHandler.getEntry(i).getIntoNode()
                entryName = entry.getName()[:-6]
                #print('entryFound:', entryName)

                enemy = utils.enemyDictionary[entryName]
                if enemy is not None and not enemy.getIsDead():
                    if utils.getIsInRange(self.playerNode.getPos(), enemy.enemyNode.getPos(), self.combatRange):
                        bAttacked = self.attack(enemy) # Returns 1 if player attacked but did not hit, returns 2 on hit

                        if bAttacked == 2:
                            enemy.enemyModel.play('hit')

            # Only play animations if player actually attacked
            if bAttacked != 0:
                #print('attackEnemies')
                self.playerModel.play('attack')

                for i in range(numEntries):
                    enemyTargetName = self.attackCollisionHandler.getEntry(i).getIntoNode().getName()[:-6]
                    enemyTarget = utils.enemyDictionary[enemyTargetName]

                    if enemyTarget is not None and not enemyTarget.getIsDead():
                        self.setCurrentTarget(enemyTarget)
                        break;

            return task.again

        else:
            #print('go to idle')
            self.removeCurrentTarget()

            if self.state == 'Combat':
                self.request('Idle')

            return task.done


#----------------------- PLAYER STATES --------------------------------------#
    def enterRun(self):
        self.playerModel.loop('run', fromFrame=0, toFrame=12)

    def exitRun(self):
        self.playerModel.stop()

    def enterCombat(self):
        #print('enterCombat')
        self.playerModel.stop()
        self.destination = self.playerNode.getPos()

        attackDelay = self.getInitiativeRoll()
        self.combatTask = taskMgr.doMethodLater(attackDelay, self.attackEnemies, 'combatTask')

        self._hudRef.printFeedback('In combat', True)

    def exitCombat(self):
        #print('exitCombat')
        taskMgr.remove(self.combatTask)
        self._hudRef.printFeedback('Combat ended', False)

    def enterIdle(self):
        stopPlayer = self.playerModel.actorInterval('stop', loop=0)
        idlePlayer = Func(self.playerModel.loop, 'idle', fromFrame=0, toFrame=50)

        self.stopMovingSequence = Sequence(stopPlayer, idlePlayer)
        self.stopMovingSequence.start()

    def exitIdle(self):
        self.stopMovingSequence.finish()

    def enterDeath(self):
        self.playerModel.play('death')

        self.deathCount += 1

        taskMgr.doMethodLater(3, self.respawn, 'respawnTask')

    def exitDeath(self):
        print('exitDeath')

#--------------------- PLAYER DEATH ---------------------------#
    def respawn(self, task):
        self._hudRef.printFeedback('Respawning')

        # Move player back to start pos
        self.destination = self.startPos
        self.playerNode.setPos(self.startPos)

        # Heal the player again
        self.fullHeal()

        # Make sure that isDead variable is set to false
        self.setIsNotDead()

        # Reset state back to idle
        self.request('Idle')

        return task.done