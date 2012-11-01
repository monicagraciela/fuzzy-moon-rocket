from panda3d.core import *
import utils

class Map:
    def __init__(self, parentNode):
        print("Map class instantiated")
        self.initSun(parentNode)
        self.initGround(parentNode)
        #self.initWalls(parentNode)
        #self.initFog(parentNode)

    def initSun(self, parentNode):
        # Setup directional light
        dlight = DirectionalLight('dlight')
        dlight.setColor(VBase4(1, 1, 0.5, 1))

        self.dlightNode = parentNode.attachNewNode(dlight)
        self.dlightNode.setHpr(0, -150, 0)
        parentNode.setLight(self.dlightNode)

        # Setup spot light (works better with shadow casting)
        #self.spotLight = parentNode.attachNewNode(Spotlight('Spot'))
        #self.spotLight.setPos(0, -200, 200)
        #self.spotLight.lookAt(0, 0, 0)
        #parentNode.setLight(self.spotLight)

        #self.spotLight.node().setShadowCaster(True, 2024, 2024)
        #self.spotLight.node().showFrustum()
        #self.spotLight.node().getLens().setFov(80)
        #self.spotLight.node().getLens().setNearFar(20, 400)

        #parentNode.setShaderAuto()

    def initGround(self, parentNode):
        # Setup environment (plane)
        self.areaNode = parentNode.attachNewNode('areaNode')

        areaModel = loader.loadModel('models/area_1.egg')
        areaModel.reparentTo(self.areaNode)

        # Make sure area is centered in world and that it has recognizable name
        self.areaNode.setPos(0, 0, 0)
        #self.areaNode.setName('ground')

        # The ground is the walk plane, it collides with mouse ray and player- and enemies ground rays
        self.ground = areaModel.find('**/ground')
        self.ground.setCollideMask(BitMask32.bit(1))

        # Colliders are obstacles in areas, they collide with enemies and the player
        self.collidersGroup = areaModel.find('**/colliders')
        self.collidersGroup.setCollideMask(BitMask32.bit(2))

        # Locate starting and exiting positions
        self.startPos = areaModel.find('**/startPos').getPos()
        self.exitPos = areaModel.find('**/exitPos').getPos()

        self.initWalls(self.areaNode)

        area2Model = loader.loadModel('models/area_2.egg')
        area2Model.reparentTo(self.areaNode)

        area2Model.setPos(0, -200, 0)

        self.ground2 = area2Model.find('**/ground')
        self.ground2.setCollideMask(BitMask32.bit(1))

        # Colliders are obstacles in areas, they collide with enemies and the player
        self.collidersGroup2 = area2Model.find('**/collision_geoms')
        self.collidersGroup2.setCollideMask(BitMask32.bit(2))

    def initWalls(self, parentNode):
        walls = loader.loadModel('models/walls.egg')
        walls.reparentTo(parentNode)

        walls.setPos(0, 0, 0)

        walls.setCollideMask(BitMask32.allOff())

        collisionWalls = walls.find('**/collisionWalls')
        collisionWalls.setCollideMask(BitMask32.bit(2))

    def initFog(self, parentNode):
        # Setup fog 
        self.fog = Fog('Fog1')
        self.fog.setColor(0.1, 0.25, 0.25)
        self.fog.setExpDensity(0.05)
        parentNode.setFog(self.fog)

