import cocos

class GameView(cocos.layer.ColorLayer):
	def __init__(self, model):
		super(GameView, self).__init__(255, 255, 255, 255)
		self.model = model

		self.add(self.model.player)
		self.add(self.model.player_bullets)
		self.add(self.model.enemies)
