from panda3d.core import *

class DDA():

    SpeedFactor = 1.0
    EXPFactor = 20.0

    def __init__(self, mainRef):
        print("DDA class instantiated")

        self._enemyListRef = mainRef.enemyList

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

    def running_avg(self, nums):
        # sum = 0
        # for count, number in enumerate(numbers):
        #     sum += number
        #     yield sum/(count+1)
        avgList = [sum(nums[:count])/count for count in xrange(1, len(nums)+1)]
        #print 'running_avg result:', result[len(result)-1]
        return avgList[len(avgList)-1]

    def monitorDDA(self, task):
        task.count += 1

        self.enemyDeathHistory.append(self.enemyDeathCount)
        self.enemyDeathCount = 0
        self.enemyDeathTotalCount += self.enemyDeathCount

        player = self._playerRef

        if len(player.healthHistory) > 1 and task.count > 0:
            lastSixtySeconds = player.healthHistory[-60:]
            #print 'lastSixtySeconds len:', len(lastSixtySeconds)

            self.playerAverageHealthPerSecond = self.running_avg(lastSixtySeconds)
            #print 'playerAverageHealthPerSecond:', self.playerAverageHealthPerSecond

            self.healthGobletModifier = 1 - (self.playerAverageHealthPerSecond / player.maxHealthPoints)
            #print 'healthGobletModifier:', self.healthGobletModifier

        return task.again