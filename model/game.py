import pyglet
from pyglet.gl import *
import cocos
from cocos.director import director
from cocos.actions import *
import math
import random
import level

class GameModel(pyglet.event.EventDispatcher):
	def __init__(self):
		super(GameModel, self).__init__()

		# Testing wave class
		wave1 = level.Wave([(3, None), (4, None), (5, None)])
		self.level = level.Level([wave1])
		for e in self.level.current_wave.get_children():
			e.push_handlers(self)
			
		# Add the player
		self.player = Player()
		self.player.position = 400, 300
		
		# Node for player bullets
		self.player_bullets = cocos.batch.BatchNode()
		
		# Node for enemy bullets
		self.enemy_bullets = cocos.batch.BatchNode()

		# Register player event listeners
		self.player.push_handlers(self)
	
	def on_game_over(self):
		import getgameover
		director.replace(getgameover.get_scene())
	
	def fire_player_bullet(self, bullet):
		bullet.position = self.player.position
		self.player_bullets.add(bullet)

	def on_player_fire(self, bullet):
		self.player_bullets.add(bullet)

	def on_enemy_fire(self, bullet):
		self.enemy_bullets.add(bullet)

	def step(self, dt):
		"""Called every frame, this method updates objects that have time dependent calculations to perform.
		"""
		# Some inefficient naive collision detection
		for b in self.player_bullets.get_children():
			for e in self.level.current_wave.get_children():
				if b.get_rect().intersects(e.get_rect()):
					b.on_hit(e)
					self.player_bullets.remove(b)
					return
		if not self.player.no_clip:
			for e in self.level.current_wave.get_children():
				if self.player.get_rect().intersects(e.get_rect()):
					self.player.on_hit()
					return
			for b in self.enemy_bullets.get_children():
				if b.get_rect().intersects(self.player.get_rect()):
					b.on_hit(self.player)
					self.enemy_bullets.remove(b)
					return

class RemoveBoundedMove(cocos.actions.move_actions.Move):
	"""Move the target but remove it from the parent when it reaches certain bounds.
	Modified from the cocos2d sources to fit the needed purpose.
	"""
	def init(self, width, height):
		self.width, self.height = width, height

	def step(self, dt):
		super(RemoveBoundedMove, self).step(dt)
		x, y = self.target.position
		w, h = self.target.width, self.target.height
		# Out of bounds, remove the node from the parent
		if x > self.width + w/2 or x < 0 - w/2 or y > self.height + h/2 or y < 0 - h/2:
			self.target.parent.remove(self.target)

		self.target.position = (x, y)

class Bullet(cocos.sprite.Sprite):
	"""Provides the functionality to create differing bullet types by using event handlers.
	"""
	def __init__(self, image_file, dx=0, dy=500):
		"""dx and dy parameters set the bullet speed and vector.
		"""
		super(Bullet, self).__init__(image_file)
		self.velocity = dx, dy
		w, h = director.get_window_size()
		self.do(RemoveBoundedMove(w, h))
	
	def step(self, dt):
		self.x += self.dx * dt
		self.y += self.dy * dt

	def on_hit(self, entity):
		"""Hit event handler.
		Customize this to do what you want the bullet to do.
		"""
		pass

class RotateCWBullet(Bullet):
	"""Bullet that will rotate an enemy's kill vertex one 'step' clockwise.
	"""
	def __init__(self):
		super(RotateCWBullet, self).__init__('rotate_cw_bullet.png')
	
	def on_hit(self, entity):
		if entity.no_shield:
			entity.rotate_cw()

class RotateCCWBullet(Bullet):
	"""Bullet that will rotate an enemy's kill vertex one 'step' counter clockwise.
	"""
	def __init__(self):
		super(RotateCCWBullet, self).__init__('rotate_ccw_bullet.png')
	
	def on_hit(self, entity):
		if entity.no_shield:
			entity.rotate_ccw()
		
class FlipLeftBullet(Bullet):
	"""Bullet that will flip an enemy by it's left axis of symmetry.
	"""
	def __init__(self):
		super(FlipLeftBullet, self).__init__('flip_left_bullet.png')
	
	def on_hit(self, entity):
		if entity.no_shield:
			entity.flip_l()

class FlipRightBullet(Bullet):
	"""Bullet that will flip an enemy by it's right axis of symmetry.
	"""
	def __init__(self):
		super(FlipRightBullet, self).__init__('flip_right_bullet.png')
	
	def on_hit(self, entity):
		if entity.no_shield:
			entity.flip_r()

class KillBullet(Bullet):
	"""Bullet that will kill an enemy that has its kill vertex exposed.
	"""
	def __init__(self):
		super(KillBullet, self).__init__('bullet.png')
	
	def on_hit(self, entity):
		if entity.kill_vertex == 0:
			entity.on_death()

class EnemyBullet(Bullet):
	"""Enemies fire these. Go figure.
	"""
	def __init__(self):
		super(EnemyBullet, self).__init__('enemy_bullet.png', dy=-300)
	
	def on_hit(self, entity):
		# Player loses a life
		entity.lose_life()

class Player(cocos.sprite.Sprite):
	""" Our courageous hero!
	"""
	# Fuck yeah bit masks!
	MOVE_LEFT = 1
	MOVE_RIGHT = 2
	MOVE_UP = 4
	MOVE_DOWN = 8

	def __init__(self):
		cocos.sprite.Sprite.__init__(self, 'ship.png')
		self.move_mask = 0
		self.speed = 500
		w, h = director.get_window_size()
		self.do(cocos.actions.move_actions.BoundedMove(w, h))
		self.velocity = 0, 0
		self.no_clip = False
		self.lives = 3

	def move(self, direction):
		self.move_mask |= direction
		self.update_velocity()
	
	def stop_move(self, direction):
		self.move_mask &= ~direction
		self.update_velocity()
	
	def fire(self, bullet):
		bullet.position = self.position
		self.dispatch_event('on_player_fire', bullet)
	
	def update_velocity(self):
		dx = 0
		dy = 0

		if self.move_mask & self.MOVE_LEFT:
			dx = -self.speed
		if self.move_mask & self.MOVE_RIGHT:
			dx = self.speed
		if self.move_mask & self.MOVE_UP:
			dy = self.speed
		if self.move_mask & self.MOVE_DOWN:
			dy = -self.speed

		self.velocity = (dx, dy)
	
	def lose_life(self):
		def func():
			self.no_clip = False
		self.no_clip = True
		self.do(cocos.actions.Blink(20, 3) + cocos.actions.CallFunc(func))
		self.lives -= 1
		if self.lives == 0:
			self.dispatch_event('on_game_over')
	
	def on_hit(self):
		self.lose_life()

Player.register_event_type('on_game_over')
Player.register_event_type('on_player_fire')

class EnemyWeapon(object):
	"""Controls the pattern and rate with which the enemy fires bullets
	"""
	def __init__(self, enemy, interval):
		self.enemy = enemy
		def fire():
			bullet = EnemyBullet()
			bullet.position = self.enemy.position
			self.enemy.dispatch_event('on_enemy_fire', bullet)
		action = Repeat(Delay(2) + (CallFunc(fire) + Delay(.2)) * 3)
		self.enemy.do(action)
	
	def fire(self, dt):
		bullet = EnemyBullet()
		bullet.position = self.enemy.position
		self.enemy.dispatch_event('on_enemy_fire', bullet)

class EnemyPolygon(cocos.cocosnode.CocosNode, pyglet.event.EventDispatcher):
	"""Our polygonal adversary.
	"""

	# Transformation constants for tracking last transformation applied
	ROTATE_CW = 1	
	ROTATE_CCW = 2
	FLIP_L = 3
	FLIP_R = 4

	def __init__(self, num_vertices, radius=30, image_file='enemy.png'):
		#super(EnemyPolygon, self).__init__()
		cocos.cocosnode.CocosNode.__init__(self)
		pyglet.event.EventDispatcher.__init__(self)
		self.num_vertices = num_vertices
		# Maximum number of transforms to expose a kill vertex in the worst case is floor(n / 2)
		# We're dealing with ints so no need to floor the value
		self.max_hits = self.num_vertices / 2
		self.radius = radius
		# Sprites that give a visual cue as to whether the kill vertex is exposed or not.
		self.no = cocos.sprite.Sprite('no.png')
		self.yes = cocos.sprite.Sprite('yes.png')
		# Enemy sprite
		# TODO: This will be customized on a per-enemy basis
		self.sprite = cocos.sprite.Sprite(image_file)
		self.add(self.sprite)
		# Assign the kill vertex to a non-downward vertex. The polygon's
		# downward vertex is zero, and the rest are numbered
		# incrementally counter-clockwise from the downward vertex.
		self.kill_vertex = random.randrange(0, num_vertices)
		self.update_sprites()
		# Test weapon
		self.weapon = EnemyWeapon(self, 1)
		# Last transformation applied to this enemy
		self.last_transform = 0
		# Enemy shield - activated when player mistransforms
		self.no_shield = True
	
	def get_rect(self):
		rect = self.sprite.get_rect()
		rect.center = self.position
		return rect
	
	def update_sprites(self):
		"""Sets the correct sprites based upon the kill vertex.
		"""
		if self.kill_vertex == 0:
			# This is a bit of a hack... it's just not pretty. It works, though.
			# Catch element not found exceptions
			try:
				self.remove(self.no)
			except:
				pass
			self.add(self.yes)
			angle = 2 * math.pi * self.kill_vertex / self.num_vertices - math.pi / 2
			self.yes.position = self.radius * math.cos(angle), self.radius * math.sin(angle)
		else:
			try:
				self.remove(self.yes)
			except:
				pass
			self.add(self.no)
			angle = 2 * math.pi * self.kill_vertex / self.num_vertices - math.pi / 2
			self.no.position = self.radius * math.cos(angle), self.radius * math.sin(angle)

	# Rotate clockwise
	def rotate_cw(self):
		if self.last_transform != self.ROTATE_CW:
			self.kill_vertex = (self.kill_vertex - 1) % self.num_vertices
			self.update_sprites()
			self.last_transform = self.ROTATE_CW
		else:
			self.on_bad_transform()

	# Rotate counter-clockwise
	def rotate_ccw(self):
		if self.last_transform != self.ROTATE_CCW:
			self.kill_vertex = (self.kill_vertex + 1) % self.num_vertices
			self.update_sprites()
			self.last_transform = self.ROTATE_CCW
		else:
			self.on_bad_transform()

	# Flip about line of symmetry passing through the side directly
	# to the left of the downward vertex
	def flip_l(self):
		if self.last_transform != self.FLIP_L:
			self.kill_vertex = (-self.kill_vertex - 1) % self.num_vertices
			self.update_sprites()
			self.last_transform = self.FLIP_L
		else:
			self.on_bad_transform()

	# Flip about line of symmetry passing through the side directly
	# to the right of the downward vertex
	def flip_r(self):
		if self.last_transform != self.FLIP_R:
			self.kill_vertex = (-self.kill_vertex + 1) % self.num_vertices
			self.update_sprites()
			self.last_transform = self.FLIP_R
		else:
			self.on_bad_transform()

	def on_bad_transform(self):
		def shield_up():
			self.no_shield = False
		def shield_down():
			self.no_shield = True
		self.do(cocos.actions.CallFunc(shield_up) + Delay(3) +
			cocos.actions.CallFunc(shield_down))

	# Need to work out the OpenGL/pyglet vertex buffer business here, but
	# here's a sketch for how we can draw the polygon and its
	# kill vertex:
	def draw(self):
		glPushMatrix()
		self.transform()
		# Draw polygon
		if self.kill_vertex != 0:
			glColor3f(1.0, 0.0, 0.0) # red color
		else:
			glColor3f(0.0, 1.0, 0.0)
		if not self.no_shield:
			glColor3f(0.0, 0.0, 1.0)
		glLineWidth(4)
		glEnable(GL_LINE_SMOOTH)
		# Construct polygon by its vertices, starting with the
		# downward vertex and working counter-clockwise
		# TODO: Put this stuff in a vertex buffer
		glBegin(GL_LINE_LOOP)
		for i in range(self.num_vertices):
			angle = 2 * math.pi * i / self.num_vertices - math.pi / 2
			glVertex2f(self.radius * math.cos(angle), self.radius * math.sin(angle))
		glEnd()

		# Draw kill vertex indicator
		# TODO: This should be a child node
		'''kv_ind_size = 5 # Size of kill vertex indicator
		glColor3f(1.0, 0.0, 0.0) # Red color
		angle = 2 * math.pi * self.kill_vertex / self.num_vertices - math.pi / 2
		kv_ind_x = self.radius * math.cos(angle)
		kv_ind_y = self.radius * math.sin(angle)
		glPushMatrix()
		glTranslatef(kv_ind_x, kv_ind_y, 0)
		glBegin(GL_QUADS)
		glVertex2f(-kv_ind_size, -kv_ind_size)
		glVertex2f(-kv_ind_size, kv_ind_size)
		glVertex2f(kv_ind_size, kv_ind_size)
		glVertex2f(kv_ind_size, -kv_ind_size)
		glEnd()
		glPopMatrix()'''
		glPopMatrix()

	# Manage the death of the enemy polygon
	def on_death(self):
		self.dispatch_event('on_enemy_death', self)
	
EnemyPolygon.register_event_type('on_enemy_fire')
EnemyPolygon.register_event_type('on_enemy_death')
