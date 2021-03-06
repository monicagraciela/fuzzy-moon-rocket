from panda3d.core import *

class DDA():

    EXPFactor = 20.0
    maxLevelDifference = 1 # Maximum level difference between player and enemy before enemy levels up

    def __init__(self, mainRef):
        print("DDA class instantiated")

        self._enemyListRef = mainRef.enemyList

        if mainRef.scenarioHandler.getHasDDA():
            self.initEnemyDDA()

            monitorDDATask = taskMgr.doMethodLater(1, self.monitorDDA, 'monitorDDATask')
            monitorDDATask.count = 0

    def initEnemyDDA(self):
        self.enemyDeathHistory = []
        self.enemyDeathCount = 0
        self.enemyDeathTotalCount = 0

    def initPlayerDDA(self, playerRef):
        self._playerRef = playerRef

        #self.playerAverageHealthPerMinute = 0.0
        self.playerAverageHealthPerSecond = 0.0

        self.healthGobletModifier = 0.0

    def getAverage(self, nums):
        avgList = [sum(nums[:count])/count for count in xrange(1, len(nums)+1)]
        return avgList[len(avgList)-1]

    def monitorDDA(self, task):
        task.count += 1

        self.enemyDeathHistory.append(self.enemyDeathCount)
        self.enemyDeathCount = 0
        self.enemyDeathTotalCount += self.enemyDeathCount

        if task.count > 0:
            player = self._playerRef

            if len(player.healthHistory) > 1:
                lastSixtySecondsHealth = player.healthHistory[-60:]
                #print 'lastSixtySeconds len:', len(lastSixtySeconds)

                self.playerAverageHealthPerSecond = self.getAverage(lastSixtySecondsHealth)
                #print 'playerAverageHealthPerSecond:', self.playerAverageHealthPerSecond

                self.healthGobletModifier = 1 - (self.playerAverageHealthPerSecond / player.maxHealthPoints)
                #print 'healthGobletModifier:', self.healthGobletModifier

                if len(player.damageHistory) > 1:
                    lastTwelveSecondsDamage = sum(player.damageHistory[-12:])

                    self.attackBonusModifier = (self.playerAverageHealthPerSecond - lastTwelveSecondsDamage) / 2
                    #print 'attackBonusModifier:', self.attackBonusModifier

        return task.again