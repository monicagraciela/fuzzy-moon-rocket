from panda3d.core import loadPrcFileData

#loadPrcFileData('', 'fullscreen 1')
loadPrcFileData('', 'win-size 1366 768')
#loadPrcFileData('', 'compressed-textures 1')
loadPrcFileData('', 'basic-shaders-only #f')
loadPrcFileData('', 'window-title Fuzzy Moon Rocket')
#loadPrcFileData('', 'undecorated 1')

import direct.directbase.DirectStart
from direct.showbase.ShowBase import ShowBase
from panda3d.core import *
from direct.actor.Actor import Actor
from direct.task import Task
from panda3d.ai import *
import sys

from src import utils, player, enemy, gui, hud, map, states, dda, scenario

class World(ShowBase):

    # Global debug setting
    global debug

    # Array of enemies
    enemyList = []

    def __init__(self):
        print('World class instantiated')
        # Enable or disable debugging
        debug = True

        # Set background color
        base.setBackgroundColor(0.1, 0.1, 0.1, 1)
        base.camLens.setNearFar(5.5, 500)
        #base.camLens.setFov(45)
        base.camLens.setAspectRatio(1.7778)

        # Main game node
        self.mainNode = render.attachNewNode('mainNode')

        # Enable automatic shaders on everything (allows glow map, gloss maps, shadows etc.)
        self.mainNode.setShaderAuto()

        # Create the main traverser
        base.cTrav = CollisionTraverser()
        # Fluid move prevents quantum tunnelling.
        base.cTrav.setRespectPrevTransform(True)

        # Initialize global AI
        self.initAI()

        # Instantiate other classes
        self.scenarioHandler = scenario.ScenarioHandler()
        
        self.DDAHandler = dda.DDA(self)

        self.stateHandler = states.StateHandler()

        self.mapHandler = map.Map(self)

        self.player = player.Player(self)

        #self.gui = gui.GUI()
        self.hud = hud.HUD(self.player)

        # Add keyboard commands
        self.accept('escape', self.endGame)
        self.accept('pause', self.pauseGame)
        self.accept('p', self.pauseGame)

    #------------------------------------------------------------------------------------
    # Start of debugging implementation

        if debug:
            #self.accept('shift-o', self.gui.toggleOverlayFrame)
            self.accept('shift-1', self.damagePlayer)
            self.accept('shift-2', self.killEnemy)
            self.accept('shift-3', self.zoomOut)
            self.accept('shift-4', self.outputTime)
            self.accept('shift-5', self.addEnemy)
            self.accept('shift-6', self.levelPlayerUp)
            self.accept('shift-7', self.healPlayer)
            self.accept('shift-8', self.showAllCollisions)
            self.accept('shift-9', self.printStats)
            self.accept('shift-0', self.showFPS)

            self.showCollisions = False

    def damagePlayer(self): # key 1
        self.player.receiveDamage(self.player.maxHealthPoints - utils.getD8())

    def killEnemy(self): # key 2
        self.enemy.onDeath()

    def zoomOut(self): # key 3
        scale = 2
        
        if self.player.stopCamera:
            self.player.stopCamera = False

            self.player._cameraYModifier /= scale
            self.player._cameraZModifier /= scale
        else:
            self.player.stopCamera = True

            self.player._cameraYModifier *= scale
            self.player._cameraZModifier *= scale

    def outputTime(self): # key 4
        print(str(globalClock.getFrameTime()))

    def addEnemy(self): # key 5
        attributes = enemy.koboldMinion

        newEnemy = enemy.Enemy(self, attributes)
        newEnemy.moveEnemy(self.mapHandler.exitPos.getX(), self.mapHandler.exitPos.getY())

    def levelPlayerUp(self): # key 6
        for i in range(10):
            self.player.increaseLevel()

    def healPlayer(self): # key 7
        self.player.heal(self.player.maxHealthPoints)

    def showAllCollisions(self): # key 8
        if self.showCollisions:
            base.cTrav.hideCollisions()
            self.showCollisions = False
        else:
            base.cTrav.showCollisions(base.render)
            self.showCollisions = True

    def printStats(self): # key 9
        print('Strength: ' + str(self.player.strength))
        print('Constitution: ' + str(self.player.constitution))
        print('Dexterity: ' + str(self.player.dexterity))
        print('Movement speed: ' + str(self.player.movementSpeed))
        print('Combat range: ' + str(self.player.combatRange))
        print('Current health: ' + str(self.player.currentHealthPoints))
        print('Max health: ' + str(self.player.maxHealthPoints))
        print('Position: ' + str(self.player.playerNode.getPos()))
        if self.player.getCurrentTarget() is not None:
            print('Target pos: ' + str(self.player.getCurrentTarget().enemyNode.getPos()))

    def showFPS(self): # Key 0
        base.setFrameRateMeter(True)
    # End of debugging implementation
    #------------------------------------------------------------------------------------

    def initAI(self):
        # Create the AI world
        self.AIworld = AIWorld(self.mainNode)

        # AI World update
        AiUpdateTask = taskMgr.add(self.AiUpdate, 'AIUpdateTask')
        AiUpdateTask.last = 0

    def AiUpdate(self, task):
        if self.stateHandler.state != self.stateHandler.PLAY:
            return task.cont

        # Make sure we're not taking too long
        deltaTime = task.time - task.last
        task.last = task.time

        if deltaTime > .2:
            return task.cont

        # Update Ai world
        self.AIworld.update()

        return task.cont

    def pauseGame(self):
        if self.stateHandler.state == self.stateHandler.PAUSE:
            self.stateHandler.request(self.stateHandler.PLAY)
        else:
            self.stateHandler.request(self.stateHandler.PAUSE)

    def endGame(self):
        sys.exit(0)

World()
run()
