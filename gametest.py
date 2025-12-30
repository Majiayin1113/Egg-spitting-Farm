"""Z-path ball drop mini-game for quick playtesting."""

from __future__ import annotations

import math
import random
from bisect import bisect_left
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import pygame


WIDTH, HEIGHT = 820, 620
SHOP_WIDTH = 140
UTILITY_WIDTH = 150
FONT_LARGE_SIZE = 30
FONT_SMALL_SIZE = 16
BG_COLOR = (12, 16, 25)
TRACK_COLOR = (51, 178, 255)
TRACK_NODE_COLOR = (255, 255, 255)
TRACK_NODE_RADIUS = 3
MACHINE_COLOR = (255, 180, 64)
PANEL_COLOR = (24, 34, 52)
PANEL_BORDER = (90, 110, 160)
BALL_COLORS = [(255, 92, 138), (255, 214, 102), (130, 255, 173), (138, 189, 255)]
TRACK_NODE_COUNT = 40
TRACK_POINT_TOLERANCE = 1e-4

SPAWN_INTERVAL = 0.3
ROUND_TIME = 60
LEVEL_CONFIG = {
	1: {"target": 180, "blocks": False},
	2: {"target": 300, "blocks": True},
	3: {"target": 3000, "blocks": True},
	4: {"target": 20000, "blocks": True},
}
PIPE_COST_SCHEDULE = [10, 20, 25, 40, 60,180,250,400,600,800,1000,1500,2000,3000,5000]
PIPE_HEIGHT = 180
PIPE_SPEED = 1000
BALL_RADIUS = 12
# Speeds now expressed in pixels/sec to match physical distance model
BALL_ACCEL = 180.0
BALL_MAX_SPEED = 480.0
BLOCK_COST = 20
BLOCK_SLOW_FACTOR = 0.35
BLOCK_BONUS = 2
BLOCK_DURATION = 5.0
BLOCK_COOLDOWN_DURATION = 30.0
BLOCK_COOLDOWN_REDUCTION_STEPS = [10.0, 5.0, 2.0, 1.0]
BLOCK_UPGRADED_DURATION = 10.0
BLOCK_ACTIVE_COLOR = (255, 140, 90)
BLOCK_COOLDOWN_COLOR = (120, 90, 70)
BLOCK_COST_SCHEDULE = [16, 25, 30, 38, 40, 50,100,150,200,250,300,400,500,800,1000,1500]
SPEED_BOOST_DURATION = 3.0
SPEED_BOOST_FACTOR = 2.0
SPEED_BOOST_COOLDOWN = 20.0
SPECIAL_EGG_VALUE = 10
SPECIAL_EGG_COLORS = ((255, 250, 160), (255, 110, 150))
COIN_RAIN_RATE = 5
SKILL_BUTTON_HEIGHT = 32
SKILL_PANEL_MARGIN = 16
SKILL_INFO = {
	"super_egg": {"title": "Lucky Egg", "desc": "Every 5th egg: Super Egg (+10 pts)"},
	"coin_rain": {"title": "Coin Rain", "desc": "+5 coins/sec"},
	"rapid_fire": {"title": "Rapid Nest", "desc": "1 Extra egg every 0.5s"},
}
SKILL_COLORS = {
	"super_egg": (90, 200, 150),
	"coin_rain": (90, 140, 220),
	"rapid_fire": (255, 170, 95),
}

SHOP_ITEM_DETAILS = {
	"pipe": {
		"title": "Vertical Pipe",
		"desc": "Drop eggs through a short chute to skip ahead on the trail.",
	},
	"block": {
		"title": "Slow Block",
		"desc": "Place on the path to slow eggs and add bonus score.",
	},
	"turbo": {
		"title": "Turbo Pipe",
		"desc": "Lay a glowing lane that doubles egg speed and points along a segment.",
	},
	"bouncer": {
		"title": "Supply Pad",
		"desc": "Collect trail capsules to charge it, then place three pads to scatter 3-5 pickups.",
	},
	"portal": {
		"title": "Portal Pair",
		"desc": "Drop two gates anywhere to warp eggs forward for bursts of speed.",
	},
	"storm": {
		"title": "Egg Storm",
		"desc": "Every 20 eggs passing through detonates 30-100 instant points.",
	},
	"speed_boost": {
		"title": "Speed Surge",
		"desc": "Click to unleash x2 speed for 3s, then wait for cooldown.",
	},
}
TOOLTIP_BG = (26, 32, 48)
TOOLTIP_BORDER = (255, 255, 255)
TOOLTIP_TEXT = (230, 240, 255)

RAPID_FIRE_INTERVAL = 0.5
TURBO_PIPE_COST_SCHEDULE = [25, 45, 80, 100,250,800,1500,5000]
TURBO_PIPE_LENGTH = 0.05  # portion of the track covered
TURBO_PIPE_MULTIPLIER = 1.01
TURBO_PIPE_COLOR = (255, 120, 40)

BOUNCER_COST = 10
BOUNCER_RADIUS = 38
BOUNCER_TRIGGER_REMOVALS = 3
BOUNCER_DROP_MIN = 3
BOUNCER_DROP_MAX = 5
BOUNCER_DROP_SPREAD = 0.04
BOUNCEPAD_POWERUP_KIND = "bouncepad"

STORM_ITEM_COST = 80
STORM_MIN_EGGS = 80
STORM_MAX_EGGS = 500
STORM_WINDOW_DURATION = 5000  # milliseconds
STORM_WINDOW_TARGET = 20
STORM_ANIMATION_DURATION = 900  # milliseconds
STORM_RADIUS = 42
STORM_LIFETIME_MS = 10_000

POWERUP_DELAY_MIN = 6.0
POWERUP_DELAY_MAX = 11.0
POWERUP_PROGRESS_MIN = 0.05
POWERUP_PROGRESS_MAX = 0.95
POWERUP_MAX_ACTIVE = 3
POWERUP_RADIUS = 20
POWERUP_GLOW = (255, 220, 140)
POWERUP_BORDER = (30, 20, 50)
POWERUP_ICON_COLOR = {
	"speed_boost": (80, 200, 170),
	"storm": (190, 120, 230),
	"bouncepad": (230, 150, 255),
}
REMOVAL_BONUS = 3
REMOVAL_POPUP_DURATION = 900  # milliseconds

PORTAL_COST = 10
PORTAL_ACTIVE_DURATION = 10.0
PORTAL_RADIUS = 26
PORTAL_GLOW_COLOR = (130, 200, 255)
PORTAL_BASE_COLOR = (30, 50, 90)
PORTAL_COOLDOWN_DURATION = 40.0
PORTAL_COOLDOWN_REDUCTION = 10.0
PORTAL_INFUSION_RANGE = PORTAL_RADIUS + 14

ADVANCED_UNLOCK_LEVEL = 2  # Level where advanced abilities (e.g., speed boost) unlock
PASSIVE_UNLOCK_LEVEL = 1  # Level where the passive skill picker becomes available


def build_z_path(
	width: int,
	height: int,
	steps_per_segment: int = 36,
) -> List[Tuple[float, float]]:
	left = SHOP_WIDTH + 40
	right = width - UTILITY_WIDTH - 40
	top = 80
	mid = height // 2 - 20
	bottom = height - 70
	anchors = [
		(width // 2, top),
		(right, top + 20),
		(left, mid),
		(right, mid + 60),
		(left, bottom),
		(right, bottom + 30),
		(width // 2, height - 30),
	]
	points: List[Tuple[float, float]] = [anchors[0]]
	for start, end in zip(anchors, anchors[1:]):
		sx, sy = start
		ex, ey = end
		for step in range(1, steps_per_segment):
			ratio = step / steps_per_segment
			x = sx + (ex - sx) * ratio
			y = sy + (ey - sy) * ratio
			points.append((x, y))
		points.append(end)
	return points


def cumulative_lengths(points: Sequence[Tuple[float, float]]) -> List[float]:
	lengths = [0.0]
	total = 0.0
	for i in range(1, len(points)):
		x1, y1 = points[i - 1]
		x2, y2 = points[i]
		total += math.hypot(x2 - x1, y2 - y1)
		lengths.append(total)
	return lengths


def lerp_point(
	points: Sequence[Tuple[float, float]],
	lengths: Sequence[float],
	total_length: float,
	progress: float,
) -> Tuple[float, float]:
	if progress <= 0:
		return points[0]
	if progress >= 1:
		return points[-1]
	target = progress * total_length
	idx = bisect_left(lengths, target)
	idx = min(max(idx, 1), len(points) - 1)
	x1, y1 = points[idx - 1]
	x2, y2 = points[idx]
	seg_start = lengths[idx - 1]
	seg_end = lengths[idx]
	seg_ratio = (target - seg_start) / max(seg_end - seg_start, 1e-6)
	x = x1 + (x2 - x1) * seg_ratio
	y = y1 + (y2 - y1) * seg_ratio
	return x, y


@dataclass
class Ball:
	color_index: int
	distance: float = 0.0
	last_distance: float = 0.0
	speed: float = 0.0
	in_pipe: bool = False
	pipe_y: float = 0.0
	pipe_x: float = 0.0
	pipe_id: Optional[int] = None
	used_pipes: set[int] = field(default_factory=set)
	block_hits: set[int] = field(default_factory=set)
	turbo_hits: set[int] = field(default_factory=set)
	bonus_score: int = 0
	score_value: int = 1
	coin_value: int = 1
	is_special: bool = False


@dataclass
class PipeItem:
	id: int = 0
	cost: int = 0
	rect: Optional[pygame.Rect] = None
	entry_progress: float = 0.0
	exit_progress: float = 0.0
	entry_y: float = 0.0
	exit_y: float = 0.0
	x: float = 0.0


@dataclass
class BlockItem:
	id: int = 0
	cost: int = 0
	progress: float = 0.0
	pos: Tuple[float, float] = (0.0, 0.0)
	radius: int = 18
	spawn_ms: int = 0
	is_active: bool = False
	active_duration: float = BLOCK_DURATION
	active_until_ms: int = 0
	cooldown_duration: float = BLOCK_COOLDOWN_DURATION
	cooldown_start_ms: int = 0
	cooldown_end_ms: int = 0
	upgrade_count: int = 0


@dataclass
class TurboPipeItem:
	id: int = 0
	cost: int = 0
	start_progress: float = 0.0
	end_progress: float = 0.0
	length_progress: float = TURBO_PIPE_LENGTH
	positions: List[Tuple[float, float]] = field(default_factory=list)


@dataclass
class BouncerItem:
	id: int = 0
	cost: int = BOUNCER_COST
	center: Tuple[int, int] = (0, 0)
	progress: float = 0.0
	radius: int = BOUNCER_RADIUS
	removals_remaining: int = BOUNCER_TRIGGER_REMOVALS
	ready_to_drop: bool = False


@dataclass
class StormItem:
	id: int = 0
	cost: int = STORM_ITEM_COST
	center: Tuple[int, int] = (0, 0)
	progress: float = 0.0
	radius: int = STORM_RADIUS
	window_count: int = 0
	counted_eggs: int = 0
	animation_until: int = 0
	last_reward: int = 0
	settle_at: int = 0
	expires_at: int = 0


@dataclass
class PortalItem:
	id: int = 0
	cost: int = PORTAL_COST
	center: Tuple[int, int] = (0, 0)
	progress: float = 0.0
	radius: int = PORTAL_RADIUS


@dataclass
class TrackPowerup:
	id: int = 0
	kind: str = "speed_boost"
	progress: float = 0.0
	pos: Tuple[int, int] = (0, 0)
	radius: int = POWERUP_RADIUS


@dataclass
class CoinPopup:
	text: str
	pos: Tuple[int, int]
	expires: int


class SpiralGame:
	def __init__(self, start_level: int = 1) -> None:
		pygame.init()
		pygame.display.set_caption("Z-Trail Drop")
		self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
		self.clock = pygame.time.Clock()
		self.font_large = pygame.font.SysFont("consolas", FONT_LARGE_SIZE)
		self.font_small = pygame.font.SysFont("consolas", FONT_SMALL_SIZE)

		self.track_points = build_z_path(WIDTH, HEIGHT)
		self.track_lengths = cumulative_lengths(self.track_points)
		self.track_total = self.track_lengths[-1]
		self.track_nodes = self.build_track_nodes(TRACK_NODE_COUNT)
		self.track_node_progress = [node[2] for node in self.track_nodes]

		self.machine_pos = (WIDTH // 2, 70)
		self.shop_rect = pygame.Rect(0, 0, SHOP_WIDTH, HEIGHT)
		button_width = SHOP_WIDTH - 40
		button_height = 80
		button_gap = 16
		first_y = 120
		self.pipe_button = pygame.Rect(20, first_y, button_width, button_height)
		self.block_button = pygame.Rect(20, self.pipe_button.bottom + button_gap, button_width, button_height)
		self.portal_button = pygame.Rect(20, self.block_button.bottom + button_gap, button_width, button_height)
		self.turbo_button = pygame.Rect(20, self.portal_button.bottom + button_gap, button_width, button_height)
		self.utility_rect = pygame.Rect(WIDTH - UTILITY_WIDTH, 0, UTILITY_WIDTH, HEIGHT)
		ability_width = self.utility_rect.width - 40
		speed_boost_top = self.utility_rect.y + 40
		self.speed_boost_button = pygame.Rect(
			self.utility_rect.x + 20,
			speed_boost_top,
			ability_width,
			120,
		)
		storm_button_height = 100
		storm_button_y = self.speed_boost_button.bottom + 16
		self.storm_button = pygame.Rect(
			self.utility_rect.x + 20,
			storm_button_y,
			ability_width,
			storm_button_height,
		)
		bouncepad_button_height = 100
		bouncepad_button_y = self.storm_button.bottom + 16
		self.bouncepad_button = pygame.Rect(
			self.utility_rect.x + 20,
			bouncepad_button_y,
			ability_width,
			bouncepad_button_height,
		)
		skill_panel_top = self.bouncepad_button.bottom + 20
		available_height = max(180, self.utility_rect.bottom - skill_panel_top - 20)
		self.skill_panel_rect = pygame.Rect(
			self.utility_rect.x + 10,
			skill_panel_top,
			self.utility_rect.width - 20,
			min(320, available_height),
		)
		icon_size = SKILL_BUTTON_HEIGHT
		btn_x = self.skill_panel_rect.centerx - icon_size // 2
		btn_y = self.skill_panel_rect.y + 52
		skill_spacing = icon_size + 8
		self.skill_buttons = {
			"super_egg": pygame.Rect(btn_x, btn_y, icon_size, icon_size),
			"coin_rain": pygame.Rect(btn_x, btn_y + skill_spacing, icon_size, icon_size),
			"rapid_fire": pygame.Rect(
				btn_x,
				btn_y + 2 * skill_spacing,
				icon_size,
				icon_size,
			),
		}
		self.track_powerups: List[TrackPowerup] = []
		self.powerup_counter = 0
		self.powerup_spawn_timer = 0.0
		self.powerup_spawn_delay = self.next_powerup_delay()
		self.coin_popups: List[CoinPopup] = []
		self.pipe_counter = 0
		self.pipe_purchases = 0
		self.block_counter = 0
		self.block_purchases = 0
		self.pipes: List[PipeItem] = []
		self.blocks: List[BlockItem] = []
		self.turbo_counter = 0
		self.turbo_purchases = 0
		self.turbo_pipes: List[TurboPipeItem] = []
		self.bouncer_counter = 0
		self.bouncer_purchases = 0
		self.bouncers: List[BouncerItem] = []
		self.placing_bouncer: Optional[BouncerItem] = None
		self.storm_counter = 0
		self.storm_emitters: List[StormItem] = []
		self.placing_storm: Optional[StormItem] = None
		self.portal_counter = 0
		self.portal_purchases = 0
		self.portals: List[PortalItem] = []
		self.placing_portal: Optional[PortalItem] = None
		self.portal_state: str = "inactive"
		self.portal_active_until = 0
		self.portal_cooldown_until = 0
		self.placing_pipe: Optional[PipeItem] = None
		self.placing_block: Optional[BlockItem] = None
		self.placing_turbo_pipe: Optional[TurboPipeItem] = None
		self.speed_boost_active_until = 0
		self.speed_boost_cooldown_until = 0
		self.speed_boost_unlocked = False
		self.active_skills: set[str] = set()
		self.skill_selection_required = False
		self.skill_coin_timer = 0.0
		self.rapid_fire_timer = 0.0
		self.skill_modal_buttons: Dict[str, pygame.Rect] = {}
		self.skill_confirm_button: Optional[pygame.Rect] = None
		self.speed_boost_charges = 0
		self.storm_charges = 0
		self.bouncepad_charges = 0
		self.shop_tooltip_data: Optional[Dict[str, Optional[str]]] = None
		self.spawned_ball_count = 0
		self.level_configs = LEVEL_CONFIG
		self.max_level = max(self.level_configs.keys()) if self.level_configs else 1
		self.current_level = max(1, min(start_level, self.max_level))
		self.reset_round()

	def reset_round(self, level: Optional[int] = None, carry_items: bool = False) -> None:
		if level is not None:
			self.current_level = max(1, min(level, self.max_level))
		if carry_items:
			preserved_pipes = self.clone_pipes()
			preserved_blocks = self.clone_blocks()
			preserved_turbos = self.clone_turbo_pipes()
			preserved_bouncers = self.clone_bouncers()
			preserved_storms = self.clone_storm_emitters()
			preserved_portals = self.clone_portals()
			pipe_counter = self.pipe_counter
			block_counter = self.block_counter
			turbo_counter = self.turbo_counter
			bouncer_counter = self.bouncer_counter
			bouncer_purchases = getattr(self, "bouncer_purchases", 0)
			storm_counter = self.storm_counter
			portal_counter = self.portal_counter
			portal_purchases = getattr(self, "portal_purchases", 0)
			pipe_purchases = getattr(self, "pipe_purchases", 0)
			block_purchases = getattr(self, "block_purchases", 0)
			turbo_purchases = getattr(self, "turbo_purchases", 0)
		else:
			preserved_pipes = []
			preserved_blocks = []
			preserved_turbos = []
			preserved_bouncers = []
			preserved_storms = []
			preserved_portals = []
			pipe_counter = 0
			block_counter = 0
			turbo_counter = 0
			bouncer_counter = 0
			bouncer_purchases = 0
			storm_counter = 0
			portal_counter = 0
			portal_purchases = 0
			pipe_purchases = 0
			block_purchases = 0
			turbo_purchases = 0
		self.balls: List[Ball] = []
		self.score = 0
		self.coins = 0
		self.spawn_timer = 0.0
		self.round_start_ms: Optional[int] = None
		self.round_active = True
		self.round_result: Optional[str] = None
		self.pipes = preserved_pipes
		self.placing_pipe = None
		self.pipe_counter = pipe_counter
		self.pipe_purchases = pipe_purchases
		self.blocks = preserved_blocks
		self.block_counter = block_counter
		self.block_purchases = block_purchases
		self.placing_block = None
		self.turbo_pipes = preserved_turbos
		self.turbo_counter = turbo_counter
		self.turbo_purchases = turbo_purchases
		self.placing_turbo_pipe = None
		self.bouncers = preserved_bouncers
		self.bouncer_counter = bouncer_counter
		self.bouncer_purchases = bouncer_purchases
		self.placing_bouncer = None
		self.storm_emitters = preserved_storms
		self.storm_counter = storm_counter
		self.placing_storm = None
		self.portals = preserved_portals
		self.portal_counter = portal_counter
		self.portal_purchases = portal_purchases
		self.placing_portal = None
		self.portal_state = "inactive"
		self.portal_active_until = 0
		self.portal_cooldown_until = 0
		self.speed_boost_unlocked = self.current_level >= ADVANCED_UNLOCK_LEVEL
		self.speed_boost_active_until = 0
		self.speed_boost_cooldown_until = 0
		self.active_skills = set()
		self.skill_selection_required = self.current_level >= PASSIVE_UNLOCK_LEVEL
		self.skill_coin_timer = 0.0
		self.rapid_fire_timer = 0.0
		self.skill_modal_buttons = {}
		self.skill_confirm_button = None
		self.spawned_ball_count = 0
		self.track_powerups = []
		self.powerup_counter = 0
		self.powerup_spawn_timer = 0.0
		self.powerup_spawn_delay = self.next_powerup_delay()
		self.coin_popups = []
		self.speed_boost_charges = 0
		self.storm_charges = 0
		self.bouncepad_charges = 0
		if not self.skill_selection_required:
			self.start_round_clock()

	def start_round_clock(self) -> None:
		if self.round_start_ms is None:
			self.round_start_ms = pygame.time.get_ticks()

	def next_pipe_cost(self) -> int:
		idx = min(self.pipe_purchases, len(PIPE_COST_SCHEDULE) - 1)
		return PIPE_COST_SCHEDULE[idx]

	def next_block_cost(self) -> int:
		idx = min(self.block_purchases, len(BLOCK_COST_SCHEDULE) - 1)
		return BLOCK_COST_SCHEDULE[idx]

	def next_turbo_cost(self) -> int:
		idx = min(self.turbo_purchases, len(TURBO_PIPE_COST_SCHEDULE) - 1)
		return TURBO_PIPE_COST_SCHEDULE[idx]

	def next_portal_cost(self) -> int:
		return PORTAL_COST * (2 ** self.portal_purchases)

	def next_storm_cost(self) -> int:
		return STORM_ITEM_COST

	def level_target(self) -> int:
		cfg = self.level_configs.get(self.current_level, {})
		return cfg.get("target", 0)

	def blocks_enabled(self) -> bool:
		cfg = self.level_configs.get(self.current_level, {})
		return cfg.get("blocks", False)

	def turbo_enabled(self) -> bool:
		return self.current_level >= 3

	def bouncer_enabled(self) -> bool:
		return self.current_level >= 3

	def storm_enabled(self) -> bool:
		return self.current_level >= 3

	def portal_enabled(self) -> bool:
		return self.current_level >= 3

	def pending_bouncer_target(self) -> Optional[BouncerItem]:
		for bouncer in self.bouncers:
			if not bouncer.ready_to_drop and bouncer.removals_remaining > 0:
				return bouncer
		return None

	def bouncer_removal_status(self) -> Optional[Tuple[int, int]]:
		target = self.pending_bouncer_target()
		if not target:
			return None
		remaining = max(0, target.removals_remaining)
		progress = max(0, BOUNCER_TRIGGER_REMOVALS - remaining)
		return progress, remaining

	def handle_tool_removed(self, _kind: str) -> None:
		if not self.bouncers:
			return
		target = self.pending_bouncer_target()
		if not target:
			return
		target.removals_remaining = max(0, target.removals_remaining - 1)
		if target.removals_remaining == 0:
			target.ready_to_drop = True
		self.update_bouncer_supply()

	def speed_boost_active(self) -> bool:
		if not self.speed_boost_unlocked:
			return False
		return pygame.time.get_ticks() < self.speed_boost_active_until

	def speed_boost_multiplier(self) -> float:
		return SPEED_BOOST_FACTOR if self.speed_boost_active() else 1.0

	def speed_boost_ui_visible(self) -> bool:
		return self.speed_boost_active() or self.speed_boost_charges > 0

	def storm_ui_visible(self) -> bool:
		return self.storm_charges > 0 or self.placing_storm is not None

	def bouncepad_ui_visible(self) -> bool:
		if not self.bouncer_enabled():
			return False
		return (
			self.placing_bouncer is not None
			or self.bouncepad_charges > 0
			or bool(self.bouncers)
		)

	def next_powerup_delay(self) -> float:
		return random.uniform(POWERUP_DELAY_MIN, POWERUP_DELAY_MAX)

	def collectible_powerup_types(self) -> List[str]:
		types: List[str] = []
		if self.speed_boost_unlocked:
			types.append("speed_boost")
		if self.storm_enabled():
			types.append("storm")
		if self.bouncer_enabled():
			types.append(BOUNCEPAD_POWERUP_KIND)
		return types

	def available_skill_keys(self) -> List[str]:
		keys: List[str] = []
		if self.current_level >= 2:
			keys.append("super_egg")
		keys.append("coin_rain")
		if self.current_level >= 3:
			keys.append("rapid_fire")
		return keys

	def spawn_track_powerup(self) -> bool:
		options = self.collectible_powerup_types()
		if not options:
			return False
		for _ in range(8):
			kind = random.choice(options)
			progress = random.uniform(POWERUP_PROGRESS_MIN, POWERUP_PROGRESS_MAX)
			x, y = lerp_point(
				self.track_points,
				self.track_lengths,
				self.track_total,
				progress,
			)
			if any(
				math.hypot(x - powerup.pos[0], y - powerup.pos[1]) < POWERUP_RADIUS * 3
				for powerup in self.track_powerups
			):
				continue
			self.powerup_counter += 1
			self.track_powerups.append(
				TrackPowerup(
					id=self.powerup_counter,
					kind=kind,
					progress=progress,
					pos=(int(x), int(y)),
				)
			)
			return True
		return False

	def update_powerups(self, dt: float) -> None:
		if not self.round_active or self.round_start_ms is None:
			return
		self.powerup_spawn_timer += dt
		if not self.collectible_powerup_types():
			self.powerup_spawn_timer = 0.0
			return
		if len(self.track_powerups) >= POWERUP_MAX_ACTIVE:
			return
		if self.powerup_spawn_timer >= self.powerup_spawn_delay:
			if self.spawn_track_powerup():
				self.powerup_spawn_timer = 0.0
				self.powerup_spawn_delay = self.next_powerup_delay()

	def update_storm_emitters(self) -> None:
		if not self.storm_emitters:
			return
		now = pygame.time.get_ticks()
		active: List[StormItem] = []
		for storm in self.storm_emitters:
			if storm.settle_at and now >= storm.settle_at and storm.last_reward == 0:
				self.trigger_storm(storm)
			if storm.last_reward > 0:
				if storm.animation_until and now >= storm.animation_until:
					continue
			else:
				if storm.expires_at and storm.expires_at <= now:
					continue
			active.append(storm)
		self.storm_emitters = active

	def collect_powerup(self, powerup: TrackPowerup) -> None:
		if powerup.kind == "speed_boost":
			self.speed_boost_charges += 1
		elif powerup.kind == "storm":
			self.storm_charges += 1
		elif powerup.kind == BOUNCEPAD_POWERUP_KIND:
			self.bouncepad_charges += 1
		self.track_powerups = [item for item in self.track_powerups if item.id != powerup.id]

	def check_powerup_collision(self, ball: Ball) -> None:
		if not self.track_powerups or ball.in_pipe:
			return
		collected: List[TrackPowerup] = []
		for powerup in self.track_powerups:
			target_distance = self.progress_to_distance(powerup.progress)
			if ball.last_distance < target_distance <= ball.distance:
				collected.append(powerup)
		for powerup in collected:
			self.collect_powerup(powerup)

	def add_coin_popup(self, pos: Tuple[int, int], text: str) -> None:
		expires = pygame.time.get_ticks() + REMOVAL_POPUP_DURATION
		self.coin_popups.append(CoinPopup(text=text, pos=pos, expires=expires))

	def show_turbo_bonus_popup(self, ball: Ball, bonus: int) -> None:
		if bonus <= 0:
			return
		progress = self.ball_progress(ball)
		x, y = lerp_point(
			self.track_points,
			self.track_lengths,
			self.track_total,
			progress,
		)
		offset_y = max(20, y - (BALL_RADIUS + 12))
		self.add_coin_popup((int(x), int(offset_y)), f"+{bonus}")

	def update_coin_popups(self) -> None:
		if not self.coin_popups:
			return
		now = pygame.time.get_ticks()
		self.coin_popups = [popup for popup in self.coin_popups if popup.expires > now]

	def speed_boost_cooldown_remaining(self) -> float:
		if not self.speed_boost_unlocked:
			return 0.0
		now = pygame.time.get_ticks()
		if self.speed_boost_active() or now >= self.speed_boost_cooldown_until:
			return 0.0
		return max(0.0, (self.speed_boost_cooldown_until - now) / 1000.0)

	def can_use_speed_boost(self) -> bool:
		now = pygame.time.get_ticks()
		return (
			self.speed_boost_unlocked
			and self.speed_boost_charges > 0
			and not self.speed_boost_active()
			and now >= self.speed_boost_cooldown_until
			and self.round_active
			and self.round_start_ms is not None
		)

	def try_activate_speed_boost(self) -> None:
		if not self.can_use_speed_boost():
			return
		now = pygame.time.get_ticks()
		self.speed_boost_active_until = now + int(SPEED_BOOST_DURATION * 1000)
		self.speed_boost_cooldown_until = self.speed_boost_active_until + int(
			SPEED_BOOST_COOLDOWN * 1000
		)
		self.speed_boost_charges = max(0, self.speed_boost_charges - 1)

	def skill_status_text(self) -> str:
		if self.current_level < PASSIVE_UNLOCK_LEVEL:
			return "Passive: Locked"
		if self.active_skills:
			titles = [
				SKILL_INFO.get(key, {}).get("title", key.title())
				for key in self.available_skill_keys()
				if key in self.active_skills
			]
			return f"Passive: {', '.join(titles)}"
		if self.skill_selection_required:
			return "Passive: Choose perks"
		return "Passive: None"

	def handle_skill_selection_click(self, pos: Tuple[int, int]) -> bool:
		if self.current_level < PASSIVE_UNLOCK_LEVEL or not self.skill_selection_required:
			return False
		buttons = self.skill_modal_buttons or self.skill_buttons
		allowed = set(self.available_skill_keys())
		for key, rect in buttons.items():
			if key not in allowed:
				continue
			if rect.collidepoint(pos):
				self.toggle_skill(key)
				return True
		if self.skill_confirm_button and self.skill_confirm_button.collidepoint(pos):
			if self.active_skills:
				self.skill_selection_required = False
				self.start_round_clock()
			return True
		return False

	def toggle_skill(self, key: str) -> None:
		if key not in SKILL_INFO:
			return
		if key not in self.available_skill_keys():
			return
		if key in self.active_skills:
			self.active_skills.remove(key)
		else:
			self.active_skills.add(key)

	def spawn_ball(self) -> None:
		self.spawned_ball_count += 1
		special = "super_egg" in self.active_skills and self.spawned_ball_count % 5 == 0
		value = SPECIAL_EGG_VALUE if special else 1
		color_index = len(self.balls) % len(BALL_COLORS)
		self.balls.append(
			Ball(
				color_index=color_index,
				score_value=value,
				coin_value=value,
				is_special=special,
			)
		)

	def update_balls(self, dt: float) -> None:
		completed: List[Ball] = []
		multiplier = self.speed_boost_multiplier()
		for ball in self.balls:
			ball.last_distance = ball.distance
			if self.apply_pipe(ball, dt):
				continue
			ball.speed = min(ball.speed + BALL_ACCEL * multiplier * dt, BALL_MAX_SPEED)
			ball.distance += (ball.speed * multiplier) * dt
			if not ball.in_pipe:
				self.apply_turbo_effects(ball, dt, multiplier)
				self.apply_block_effects(ball)
				self.apply_portal_effects(ball)
				self.check_powerup_collision(ball)
				self.process_storm_pass(ball)
			if self.apply_pipe(ball, dt):
				continue
			if ball.distance >= self.track_total:
				completed.append(ball)
		if completed:
			if self.round_active:
				for fin in completed:
					score_gain = fin.score_value + fin.bonus_score
					coin_gain = fin.coin_value + fin.bonus_score
					self.score += score_gain
					self.coins += coin_gain
					self.check_round_victory()
			self.balls = [b for b in self.balls if b not in completed]

	def remaining_time(self) -> int:
		if self.round_start_ms is None:
			return ROUND_TIME
		elapsed = (pygame.time.get_ticks() - self.round_start_ms) / 1000.0
		remaining = max(0, ROUND_TIME - int(elapsed))
		if remaining == 0 and self.round_active:
			self.round_active = False
			if self.round_result != "success":
				self.round_result = "fail"
		return remaining

	def check_round_victory(self) -> None:
		if self.round_result == "success":
			return
		target = self.level_target()
		if target <= 0:
			return
		if self.score >= target:
			self.round_result = "success"

	def update(self, dt: float) -> None:
		if self.round_start_ms is None:
			return
		if self.round_active:
			self.spawn_timer += dt
			while self.spawn_timer >= SPAWN_INTERVAL:
				self.spawn_ball()
				self.spawn_timer -= SPAWN_INTERVAL
		self.update_balls(dt)
		self.update_blocks()
		self.update_bouncer_supply()
		self.update_powerups(dt)
		self.update_storm_emitters()
		self.update_coin_popups()
		self.apply_skill_income(dt)
		self.apply_rapid_fire(dt)
		self.update_portals()

	def draw_track(self) -> None:
		pygame.draw.lines(self.screen, TRACK_COLOR, False, self.track_points, 4)
		for node_x, node_y, _ in self.track_nodes:
			pygame.draw.circle(
				self.screen,
				TRACK_NODE_COLOR,
				(int(node_x), int(node_y)),
				TRACK_NODE_RADIUS,
			)
		for pipe in self.pipes:
			if pipe.rect:
				pygame.draw.rect(self.screen, (255, 255, 255), pipe.rect, border_radius=6)
		self.draw_track_powerups()
		self.draw_portals()
		self.draw_storm_emitters()
		self.draw_bouncers()
		self.draw_turbo_pipes()
		self.draw_blocks()

	def draw_machine(self) -> None:
		x, y = self.machine_pos
		rect = pygame.Rect(0, 0, 70, 40)
		rect.center = (x, y)
		pygame.draw.rect(self.screen, MACHINE_COLOR, rect, border_radius=8)
		muzzle = (int(x), int(y + 28))
		pygame.draw.circle(self.screen, MACHINE_COLOR, muzzle, 10)

	def draw_balls(self) -> None:
		for ball in self.balls:
			if ball.in_pipe:
				x, y = ball.pipe_x, ball.pipe_y
			else:
				x, y = lerp_point(
					self.track_points,
					self.track_lengths,
					self.track_total,
					self.ball_progress(ball),
				)
			if ball.is_special:
				outer, inner = SPECIAL_EGG_COLORS
				pygame.draw.circle(self.screen, outer, (int(x), int(y)), BALL_RADIUS)
				pygame.draw.circle(self.screen, inner, (int(x), int(y)), max(4, BALL_RADIUS - 4))
			else:
				color = BALL_COLORS[ball.color_index % len(BALL_COLORS)]
				pygame.draw.circle(self.screen, color, (int(x), int(y)), BALL_RADIUS)

	def draw_panel(self, remaining: int) -> None:
		rect = pygame.Rect(SHOP_WIDTH + 16, 16, 220, 150)
		pygame.draw.rect(self.screen, PANEL_COLOR, rect, border_radius=12)
		pygame.draw.rect(self.screen, PANEL_BORDER, rect, width=2, border_radius=12)

		score_text = self.font_large.render(f"Score: {self.score}", True, (255, 255, 255))
		self.screen.blit(score_text, (rect.x + 14, rect.y + 8))

		coin_text = self.font_small.render(f"Coins: {self.coins}", True, (255, 220, 140))
		self.screen.blit(coin_text, (rect.x + 14, rect.y + 50))

		timer_text = self.font_small.render(f"{remaining:02d}s", True, (180, 220, 255))
		timer_x = rect.right - timer_text.get_width() - 14
		self.screen.blit(timer_text, (timer_x, rect.y + 50))

		level_text = self.font_small.render(
			f"Level {self.current_level}", True, (180, 220, 255)
		)
		self.screen.blit(level_text, (rect.x + 14, rect.y + 78))

		target = self.level_target()
		goal_text = self.font_small.render(f"Goal: {target}", True, (255, 200, 160))
		self.screen.blit(goal_text, (rect.x + 14, rect.y + 104))

		status_y = rect.bottom - 32
		if self.round_result == "success":
			if self.current_level < self.max_level:
				next_label = self.current_level + 1
				msg = f"Press Enter for Lv {next_label}"
			else:
				msg = "Press Enter to restart"
			win_text = self.font_small.render(msg, True, (120, 255, 200))
			self.screen.blit(win_text, (rect.x + 16, status_y))
		elif not self.round_active and self.round_result == "fail":
			fail_text = self.font_small.render(
				"Press Space to retry", True, (255, 120, 120)
			)
			self.screen.blit(fail_text, (rect.x + 16, status_y))

	def draw_footer(self, remaining: int) -> None:
		if self.round_start_ms is None and self.current_level >= PASSIVE_UNLOCK_LEVEL:
			message = "Toggle passives, then press Confirm"
		elif self.round_result == "success":
			if self.current_level < self.max_level:
				next_label = self.current_level + 1
				message = f"Success! Press Enter for Level {next_label}"
			else:
				message = "All clear! Press Enter to restart"
		elif not self.round_active:
			if self.round_result == "fail":
				message = "Goal missed. Press Space to retry"
			else:
				message = "Catch every drop!"
		else:
			message = "Catch every drop!"
		text = self.font_small.render(message, True, (200, 200, 210))
		x_pos = WIDTH - UTILITY_WIDTH - text.get_width() - 20
		x_pos = max(SHOP_WIDTH + 20, x_pos)
		self.screen.blit(text, (x_pos, HEIGHT - 40))

	def draw_shop(self) -> None:
		self.shop_tooltip_data = None
		pygame.draw.rect(self.screen, (18, 26, 41), self.shop_rect)
		pygame.draw.line(self.screen, PANEL_BORDER, (SHOP_WIDTH, 0), (SHOP_WIDTH, HEIGHT), 2)
		title = self.font_small.render("Shop", True, (255, 255, 255))
		self.screen.blit(title, (20, 20))

		info = self.font_small.render("Hover for details", True, (150, 180, 210))
		self.screen.blit(info, (20, 50))

		current_cost = self.next_pipe_cost()
		btn_color = (70, 120, 200)
		if self.placing_pipe:
			btn_color = (200, 180, 80)
		elif self.coins < current_cost:
			btn_color = (45, 60, 90)
		pygame.draw.rect(self.screen, btn_color, self.pipe_button, border_radius=10)
		pygame.draw.rect(self.screen, (255, 255, 255), self.pipe_button, 2, border_radius=10)
		self.draw_shop_cost(self.pipe_button, current_cost)
		self.draw_shop_icon(self.pipe_button, "pipe")
		self.queue_shop_tooltip("pipe", self.pipe_button)

		if self.blocks_enabled():
			self.draw_block_button()
		if self.portal_enabled():
			self.draw_portal_button()
		if self.turbo_enabled():
			self.draw_turbo_button()

	def draw_power_bar(self) -> None:
		pygame.draw.rect(self.screen, (18, 26, 41), self.utility_rect)
		pygame.draw.line(
			self.screen,
			PANEL_BORDER,
			(self.utility_rect.x, 0),
			(self.utility_rect.x, HEIGHT),
			2,
		)
		title = self.font_small.render("Abilities", True, (255, 255, 255))
		self.screen.blit(title, (self.utility_rect.x + 20, 20))

		if self.speed_boost_ui_visible():
			btn_color = (70, 160, 140)
			state_msg = "Click to surge"
			note: Optional[str] = None
			locked = not self.speed_boost_unlocked
			cooldown_remaining = self.speed_boost_cooldown_remaining()
			if locked:
				btn_color = (45, 60, 90)
				state_msg = f"Unlock Lv{ADVANCED_UNLOCK_LEVEL}"
				note = state_msg
			elif self.speed_boost_active():
				btn_color = (220, 200, 90)
				state_msg = "Active"
			elif cooldown_remaining > 0:
				btn_color = (55, 80, 110)
				state_msg = "Cooldown"
				seconds = f"{cooldown_remaining:0.1f}s"
				note = f"Cooldown: {seconds}"

			pygame.draw.rect(self.screen, btn_color, self.speed_boost_button, border_radius=10)
			pygame.draw.rect(self.screen, (255, 255, 255), self.speed_boost_button, 2, border_radius=10)
			label = self.font_small.render("Speed Boost", True, (12, 16, 25))
			self.screen.blit(
				label,
				(
					self.speed_boost_button.centerx - label.get_width() // 2,
					self.speed_boost_button.y + 16,
				),
			)
			sub = self.font_small.render(f"x{SPEED_BOOST_FACTOR:.1f} speed", True, (12, 16, 25))
			self.screen.blit(
				sub,
				(
					self.speed_boost_button.centerx - sub.get_width() // 2,
					self.speed_boost_button.y + 46,
				),
			)
			state_text = self.font_small.render(state_msg, True, (12, 16, 25))
			self.screen.blit(
				state_text,
				(
					self.speed_boost_button.centerx - state_text.get_width() // 2,
					self.speed_boost_button.y + 76,
				),
			)
			if self.speed_boost_active():
				remaining = max(
					0.0, (self.speed_boost_active_until - pygame.time.get_ticks()) / 1000.0
				)
				count_text = self.font_small.render(f"{remaining:0.1f}s", True, (12, 16, 25))
				self.screen.blit(
					count_text,
					(
						self.speed_boost_button.centerx - count_text.get_width() // 2,
						self.speed_boost_button.y + 112,
					),
				)
			elif cooldown_remaining > 0:
				count_text = self.font_small.render(f"{cooldown_remaining:0.1f}s", True, (12, 16, 25))
				self.screen.blit(
					count_text,
					(
						self.speed_boost_button.centerx - count_text.get_width() // 2,
						self.speed_boost_button.y + 112,
					),
				)
			charge_label = f"Charges: {self.speed_boost_charges}"
			charge_text = self.font_small.render(charge_label, True, (12, 16, 25))
			self.screen.blit(
				charge_text,
				(
					self.speed_boost_button.centerx - charge_text.get_width() // 2,
					self.speed_boost_button.y + 96,
				),
			)
			tip_parts = [note, charge_label]
			tip_message = " · ".join(part for part in tip_parts if part)
			self.queue_shop_tooltip(
				"speed_boost",
				self.speed_boost_button,
				locked_note=tip_message or None,
			)

		if self.storm_ui_visible():
			self.draw_storm_button()
		elif not self.speed_boost_ui_visible():
			spent = self.font_small.render("Collect boosts along the trail", True, (140, 150, 180))
			self.screen.blit(
				spent,
				(
					self.utility_rect.x + 24,
					self.speed_boost_button.y + 12,
				),
			)

		self.draw_bouncepad_button()

		self.draw_skill_panel()

	def draw_storm_button(self) -> None:
		charges = max(0, self.storm_charges)
		btn_color = (150, 90, 200)
		status = "Counts 5s window"
		if self.placing_storm:
			btn_color = (220, 210, 140)
			status = "Click track to place"

		pygame.draw.rect(self.screen, btn_color, self.storm_button, border_radius=12)
		pygame.draw.rect(self.screen, (255, 255, 255), self.storm_button, 2, border_radius=12)
		title = self.font_small.render("Egg Storm", True, (12, 16, 25))
		self.screen.blit(
			title,
			(
				self.storm_button.centerx - title.get_width() // 2,
				self.storm_button.y + 8,
			),
		)
		detail = self.font_small.render("Earn 80-500 pts", True, (12, 16, 25))
		self.screen.blit(
			detail,
			(
				self.storm_button.centerx - detail.get_width() // 2,
				self.storm_button.y + 36,
			),
		)
		charge_label = "Deploying now" if self.placing_storm else f"Charge: {charges}"
		charge_text = self.font_small.render(charge_label, True, (12, 16, 25))
		self.screen.blit(
			charge_text,
			(
				self.storm_button.centerx - charge_text.get_width() // 2,
				self.storm_button.y + 58,
			),
		)
		status_text = self.font_small.render(status, True, (12, 16, 25))
		self.screen.blit(
			status_text,
			(
				self.storm_button.centerx - status_text.get_width() // 2,
				self.storm_button.bottom - 24,
			),
		)
		self.queue_shop_tooltip("storm", self.storm_button, locked_note=charge_label)

	def draw_bouncepad_button(self) -> None:
		if not self.bouncepad_ui_visible():
			return
		btn_color = (200, 120, 210)
		label = "Supply Pad"
		sub_text = "Scatter 3-5 pickups"
		status: Optional[str]
		progress_info = self.bouncer_removal_status()
		if self.placing_bouncer:
			btn_color = (230, 210, 140)
			status = "Click track to place"
		elif progress_info:
			progress_done, remaining = progress_info
			if remaining > 0:
				btn_color = (150, 110, 160)
				status = f"Sell {remaining} tools"
			else:
				btn_color = (120, 190, 150)
				status = "Drop ready"
		else:
			status = "Awaiting pad placement"
		pygame.draw.rect(self.screen, btn_color, self.bouncepad_button, border_radius=12)
		pygame.draw.rect(self.screen, (255, 255, 255), self.bouncepad_button, 2, border_radius=12)
		title = self.font_small.render(label, True, (12, 16, 25))
		self.screen.blit(
			title,
			(
				self.bouncepad_button.centerx - title.get_width() // 2,
				self.bouncepad_button.y + 8,
			),
		)
		sub = self.font_small.render(sub_text, True, (12, 16, 25))
		self.screen.blit(
			sub,
			(
				self.bouncepad_button.centerx - sub.get_width() // 2,
				self.bouncepad_button.y + 36,
			),
		)
		if progress_info:
			progress_done, remaining = progress_info
		else:
			progress_done, remaining = 0, BOUNCER_TRIGGER_REMOVALS
		progress_text = f"Removals {progress_done}/{BOUNCER_TRIGGER_REMOVALS}"
		progress_surf = self.font_small.render(progress_text, True, (12, 16, 25))
		self.screen.blit(
			progress_surf,
			(
				self.bouncepad_button.centerx - progress_surf.get_width() // 2,
				self.bouncepad_button.y + 58,
			),
		)
		charge_label = (
			"Placing now" if self.placing_bouncer else f"Charges: {max(0, self.bouncepad_charges)}"
		)
		charge_surf = self.font_small.render(charge_label, True, (12, 16, 25))
		self.screen.blit(
			charge_surf,
			(
				self.bouncepad_button.centerx - charge_surf.get_width() // 2,
				self.bouncepad_button.y + 78,
			),
		)
		if status:
			status_surf = self.font_small.render(status, True, (12, 16, 25))
			self.screen.blit(
				status_surf,
				(
					self.bouncepad_button.centerx - status_surf.get_width() // 2,
					self.bouncepad_button.bottom - 26,
				),
			)
		tip_parts = [charge_label, progress_text, status]
		locked_note = " · ".join(part for part in tip_parts if part)
		self.queue_shop_tooltip("bouncer", self.bouncepad_button, locked_note=locked_note or None)

	def draw_skill_panel(self) -> None:
		panel = self.skill_panel_rect
		pygame.draw.rect(self.screen, PANEL_COLOR, panel, border_radius=12)
		pygame.draw.rect(self.screen, PANEL_BORDER, panel, 2, border_radius=12)
		title = self.font_small.render("Passive Skills", True, (255, 255, 255))
		self.screen.blit(title, (panel.x + 12, panel.y + 10))
		unlock_short = f"Lv{PASSIVE_UNLOCK_LEVEL}"
		desc = self.font_small.render(f"Select before {unlock_short}", True, (150, 180, 210))
		self.screen.blit(desc, (panel.x + 12, panel.y + 34))
		if self.current_level < PASSIVE_UNLOCK_LEVEL:
			locked = self.font_small.render(
				f"Unlocks at Level {PASSIVE_UNLOCK_LEVEL}", True, (255, 180, 120)
			)
			self.screen.blit(locked, (panel.x + 12, panel.y + 70))
			return
		awaiting_choice = self.skill_selection_required
		icon_padding = 4
		for key in self.available_skill_keys():
			rect = self.skill_buttons.get(key)
			if rect is None:
				continue
			info = SKILL_INFO.get(key, {})
			selected = key in self.active_skills
			locked = awaiting_choice and not selected
			base_color = SKILL_COLORS.get(key, (70, 120, 200))
			icon_rect = rect.inflate(-icon_padding * 2, -icon_padding * 2)
			center = icon_rect.center
			radius = icon_rect.width // 2
			fill_color = base_color if selected else (
				max(30, base_color[0] - 30),
				max(30, base_color[1] - 30),
				max(30, base_color[2] - 30),
			)
			pygame.draw.circle(self.screen, fill_color, center, radius)
			border_color = (255, 255, 255) if selected else (120, 150, 200)
			if locked:
				border_color = (255, 200, 140)
			pygame.draw.circle(self.screen, border_color, center, radius, width=3)
			glyph = info.get("title", key.title())[:1].upper()
			glyph_text = self.font_large.render(glyph, True, (12, 16, 25))
			glyph_rect = glyph_text.get_rect(center=center)
			self.screen.blit(glyph_text, glyph_rect)
			state_label = "Active" if selected else ("Equip" if awaiting_choice else "Passive")
			state_color = (140, 255, 210) if selected else (180, 200, 220)
			state_surface = self.font_small.render(state_label, True, state_color)
			state_rect = state_surface.get_rect(center=(rect.centerx, rect.bottom + 8))
			self.screen.blit(state_surface, state_rect)
			tooltip_info = {
				"title": info.get("title", key.title()),
				"desc": info.get("desc", "Passive bonus"),
			}
			note = f"Status: {state_label}"
			self.queue_shop_tooltip(
				key,
				rect,
				locked_note=note,
				info_override=tooltip_info,
			)

	def draw_skill_overlay(self) -> None:
		if self.current_level < PASSIVE_UNLOCK_LEVEL or not self.skill_selection_required:
			self.skill_modal_buttons = {}
			self.skill_confirm_button = None
			return
		self.skill_modal_buttons = {}
		self.skill_confirm_button = None
		dimmer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
		dimmer.fill((0, 0, 0, 170))
		self.screen.blit(dimmer, (0, 0))
		panel_w, panel_h = 560, 420
		panel_rect = pygame.Rect(0, 0, panel_w, panel_h)
		panel_rect.center = (WIDTH // 2, HEIGHT // 2 - 20)
		pygame.draw.rect(self.screen, PANEL_COLOR, panel_rect, border_radius=16)
		pygame.draw.rect(self.screen, PANEL_BORDER, panel_rect, 2, border_radius=16)
		title = self.font_large.render("Select Your Passive", True, (255, 255, 255))
		self.screen.blit(title, (panel_rect.centerx - title.get_width() // 2, panel_rect.y + 20))
		sub = self.font_small.render(
			f"Toggle any perks before Level {PASSIVE_UNLOCK_LEVEL} begins",
			True,
			(180, 220, 255),
		)
		self.screen.blit(sub, (panel_rect.centerx - sub.get_width() // 2, panel_rect.y + 64))
		prompt = self.font_small.render("Click skills to toggle, then Confirm", True, (255, 220, 160))
		self.screen.blit(prompt, (panel_rect.centerx - prompt.get_width() // 2, panel_rect.y + 88))
		keys = self.available_skill_keys()
		count = max(1, len(keys))
		btn_height = 140
		cols = min(3, count)
		rows = math.ceil(count / cols)
		gap = 40
		available_width = panel_w - (cols + 1) * gap
		btn_width = max(120, available_width // cols)
		btn_y = panel_rect.y + 130
		for index, key in enumerate(keys):
			row = index // cols
			col = index % cols
			x = panel_rect.x + gap + col * (btn_width + gap)
			y = btn_y + row * (btn_height + 30)
			btn_rect = pygame.Rect(x, y, btn_width, btn_height)
			self.skill_modal_buttons[key] = btn_rect
			base_color = SKILL_COLORS.get(key, (70, 120, 200))
			if key in self.active_skills:
				base_color = (
					min(255, base_color[0] + 40),
					min(255, base_color[1] + 40),
					min(255, base_color[2] + 40),
				)
			pygame.draw.rect(self.screen, base_color, btn_rect, border_radius=14)
			pygame.draw.rect(self.screen, (255, 255, 255), btn_rect, 2, border_radius=14)
			info = SKILL_INFO.get(key, {})
			label = self.font_large.render(info.get("title", key.title()), True, (12, 16, 25))
			self.screen.blit(
				label,
				(btn_rect.centerx - label.get_width() // 2, btn_rect.y + 18),
			)
			detail = self.font_small.render(info.get("desc", "Passive bonus"), True, (12, 16, 25))
			self.screen.blit(
				detail,
				(btn_rect.centerx - detail.get_width() // 2, btn_rect.y + btn_height - 36),
			)
		confirm_w, confirm_h = 220, 50
		confirm_rect = pygame.Rect(0, 0, confirm_w, confirm_h)
		confirm_rect.centerx = panel_rect.centerx
		confirm_rect.bottom = panel_rect.bottom - 24
		enabled = bool(self.active_skills)
		color = (120, 220, 180) if enabled else (70, 80, 100)
		pygame.draw.rect(self.screen, color, confirm_rect, border_radius=12)
		pygame.draw.rect(self.screen, (255, 255, 255), confirm_rect, 2, border_radius=12)
		label = "Confirm & Start" if enabled else "Select a skill"
		text = self.font_small.render(label, True, (12, 16, 25))
		self.screen.blit(
			text,
			(confirm_rect.centerx - text.get_width() // 2, confirm_rect.centery - text.get_height() // 2),
		)
		self.skill_confirm_button = confirm_rect

	def draw_block_button(self) -> None:
		current_cost = self.next_block_cost()
		btn_color = (120, 80, 160)
		if self.placing_block:
			btn_color = (230, 200, 100)
		elif self.coins < current_cost:
			btn_color = (55, 38, 70)
		pygame.draw.rect(self.screen, btn_color, self.block_button, border_radius=10)
		pygame.draw.rect(self.screen, (255, 255, 255), self.block_button, 2, border_radius=10)
		self.draw_shop_cost(self.block_button, current_cost)
		self.draw_shop_icon(self.block_button, "block")
		self.queue_shop_tooltip("block", self.block_button)

	def draw_portal_button(self) -> None:
		cost = self.next_portal_cost()
		btn_color = (130, 190, 255)
		state_note: Optional[str] = None
		timer_text: Optional[str] = None
		now = pygame.time.get_ticks()
		if self.placing_portal:
			btn_color = (230, 210, 140)
			state_note = "Click map to set"
		elif not self.portal_enabled():
			btn_color = (45, 55, 80)
			state_note = "Unlocks at Level 3"
		elif self.coins < cost:
			btn_color = (55, 65, 95)
		elif len(self.portals) == 1:
			state_note = "Need second gate"
		elif len(self.portals) >= 2:
			if self.portal_state == "active":
				state_note = "Active"
				remaining = max(0.0, (self.portal_active_until - now) / 1000.0)
				timer_text = f"{remaining:0.1f}s"
			elif self.portal_state == "cooldown":
				state_note = "Cooldown"
				remaining = max(0.0, (self.portal_cooldown_until - now) / 1000.0)
				timer_text = f"CD {remaining:0.1f}s"
			else:
				state_note = "Priming"
		pygame.draw.rect(self.screen, btn_color, self.portal_button, border_radius=10)
		pygame.draw.rect(self.screen, (255, 255, 255), self.portal_button, 2, border_radius=10)
		self.draw_shop_cost(self.portal_button, cost)
		self.draw_shop_icon(self.portal_button, "portal")
		if timer_text:
			count_text = self.font_small.render(timer_text, True, (12, 16, 25))
			self.screen.blit(
				count_text,
				(
					self.portal_button.centerx - count_text.get_width() // 2,
					self.portal_button.y + 56,
				),
			)
		self.queue_shop_tooltip("portal", self.portal_button, locked_note=state_note)

	def draw_turbo_button(self) -> None:
		current_cost = self.next_turbo_cost()
		unlocked = self.turbo_enabled()
		btn_color = (255, 150, 90)
		if self.placing_turbo_pipe:
			btn_color = (220, 220, 120)
		elif not unlocked:
			btn_color = (55, 38, 20)
		elif self.coins < current_cost:
			btn_color = (90, 60, 45)
		pygame.draw.rect(self.screen, btn_color, self.turbo_button, border_radius=10)
		pygame.draw.rect(self.screen, (255, 255, 255), self.turbo_button, 2, border_radius=10)
		self.draw_shop_cost(self.turbo_button, current_cost)
		locked_note = None if unlocked else "Unlocks at Level 3"
		self.draw_shop_icon(self.turbo_button, "turbo")
		self.queue_shop_tooltip("turbo", self.turbo_button, locked_note=locked_note)

	def draw_blocks(self) -> None:
		now = pygame.time.get_ticks()
		for block in self.blocks:
			x, y = block.pos
			rect = pygame.Rect(0, 0, block.radius * 2, block.radius * 2)
			rect.center = (int(x), int(y))
			color = BLOCK_ACTIVE_COLOR if block.is_active else BLOCK_COOLDOWN_COLOR
			pygame.draw.rect(self.screen, color, rect, border_radius=6)
			pygame.draw.rect(self.screen, (255, 255, 255), rect, 2, border_radius=6)
			if block.is_active:
				remaining = max(0.0, (block.active_until_ms - now) / 1000.0)
			else:
				remaining = max(0.0, (block.cooldown_end_ms - now) / 1000.0)
			if remaining <= 0.0:
				continue
			seconds = int(math.ceil(remaining))
			text_color = (12, 16, 25) if block.is_active else (230, 235, 250)
			text = self.font_small.render(str(seconds), True, text_color)
			text_rect = text.get_rect(center=rect.center)
			self.screen.blit(text, text_rect)

	def draw_shop_cost(self, rect: pygame.Rect, cost: int) -> None:
		label = self.font_small.render(f"Cost: {cost}", True, (240, 240, 250))
		self.screen.blit(
			label,
			(
				rect.centerx - label.get_width() // 2,
				rect.y + 16,
			),
		)

	def draw_shop_icon(self, rect: pygame.Rect, icon_type: str) -> None:
		icon_rect = pygame.Rect(0, 0, 32, 32)
		icon_rect.center = (rect.centerx, rect.bottom - 28)
		bg = (10, 44, 66)
		pygame.draw.rect(self.screen, bg, icon_rect, border_radius=10)
		pygame.draw.rect(self.screen, (255, 255, 255), icon_rect, 2, border_radius=10)
		inner = icon_rect.inflate(-12, -12)
		if icon_type == "pipe":
			pipe_rect = pygame.Rect(0, 0, inner.width // 2, inner.height)
			pipe_rect.center = inner.center
			pygame.draw.rect(self.screen, (255, 255, 255), pipe_rect, border_radius=4)
			cap = pygame.Rect(0, 0, pipe_rect.width + 6, 6)
			cap.midbottom = pipe_rect.midtop
			pygame.draw.rect(self.screen, (255, 200, 120), cap, border_radius=3)
		elif icon_type == "block":
			square = inner.copy()
			pygame.draw.rect(self.screen, BLOCK_ACTIVE_COLOR, square, border_radius=6)
			pygame.draw.rect(self.screen, (255, 255, 255), square, 2, border_radius=6)
		elif icon_type == "turbo":
			points = [
				(inner.left, inner.bottom),
				(inner.left + inner.width * 0.4, inner.top + inner.height * 0.4),
				(inner.left + inner.width * 0.7, inner.bottom - inner.height * 0.2),
				(inner.right, inner.top),
			]
			pygame.draw.lines(self.screen, (255, 180, 90), False, points, 4)
			pygame.draw.circle(self.screen, (255, 180, 90), (int(points[0][0]), int(points[0][1])), 3)
			pygame.draw.circle(self.screen, (255, 180, 90), (int(points[-1][0]), int(points[-1][1])), 3)
		elif icon_type == "bouncer":
			center = inner.center
			r = inner.width // 2
			pygame.draw.circle(self.screen, (200, 220, 255), center, r, 2)
			pygame.draw.circle(self.screen, (120, 150, 230), center, max(2, r - 5), 1)
			pygame.draw.line(
				self.screen,
				(255, 200, 120),
				(center[0], center[1] - r),
				(center[0], center[1] + r),
				2,
			)
		elif icon_type == "portal":
			center = inner.center
			r = inner.width // 2
			pygame.draw.circle(self.screen, (120, 200, 255), center, r, 2)
			pygame.draw.circle(self.screen, (40, 60, 110), center, max(2, r - 6), 2)
			for idx in range(3):
				angle = idx * (2 * math.pi / 3)
				pt = (
					center[0] + math.cos(angle) * (r - 4),
					center[1] + math.sin(angle) * (r - 4),
				)
				pygame.draw.circle(self.screen, (255, 255, 255), (int(pt[0]), int(pt[1])), 2)

	def draw_track_powerups(self) -> None:
		if not self.track_powerups:
			return
		for powerup in self.track_powerups:
			x, y = powerup.pos
			color = POWERUP_ICON_COLOR.get(powerup.kind, (255, 255, 200))
			pygame.draw.circle(self.screen, POWERUP_GLOW, (int(x), int(y)), powerup.radius)
			pygame.draw.circle(self.screen, POWERUP_BORDER, (int(x), int(y)), powerup.radius, width=2)
			inner = max(6, powerup.radius - 6)
			pygame.draw.circle(self.screen, color, (int(x), int(y)), inner)
			glyph = "B" if powerup.kind == "speed_boost" else "E"
			text = self.font_small.render(glyph, True, (12, 16, 25))
			text_rect = text.get_rect(center=(int(x), int(y)))
			self.screen.blit(text, text_rect)

	def draw_coin_popups(self) -> None:
		if not self.coin_popups:
			return
		now = pygame.time.get_ticks()
		for popup in self.coin_popups:
			remaining = max(0, popup.expires - now)
			ratio = 1.0 - min(1.0, remaining / REMOVAL_POPUP_DURATION)
			y_offset = -30 * ratio
			alpha = max(0, 255 - int(ratio * 255))
			surface = self.font_small.render(popup.text, True, (255, 255, 255))
			render = surface.copy()
			render.set_alpha(alpha)
			rect = render.get_rect(center=(popup.pos[0], popup.pos[1] + y_offset))
			self.screen.blit(render, rect)

	def queue_shop_tooltip(
		self,
		key: str,
		rect: pygame.Rect,
		locked_note: Optional[str] = None,
		info_override: Optional[Dict[str, str]] = None,
	) -> None:
		if self.current_level >= PASSIVE_UNLOCK_LEVEL and self.skill_selection_required:
			return
		mouse_pos = pygame.mouse.get_pos()
		if not rect.collidepoint(mouse_pos):
			return
		info = info_override or SHOP_ITEM_DETAILS.get(key)
		if not info:
			return
		self.shop_tooltip_data = {
			"title": info.get("title", key.title()),
			"desc": info.get("desc", ""),
			"note": locked_note,
		}

	def draw_shop_tooltip(self) -> None:
		if not self.shop_tooltip_data:
			return
		mouse_x, mouse_y = pygame.mouse.get_pos()
		lines = [self.shop_tooltip_data.get("title", "")]
		desc = self.shop_tooltip_data.get("desc") or ""
		for segment in desc.split("\n"):
			if segment:
				lines.append(segment)
		note = self.shop_tooltip_data.get("note")
		if note:
			lines.append(note)
		padding = 10
		surfaces: List[Tuple[pygame.Surface, pygame.Rect]] = []
		max_width = 0
		for idx, text in enumerate(lines):
			if not text:
				text = " "
			surf = self.font_small.render(text, True, TOOLTIP_TEXT)
			rect = surf.get_rect()
			rect.topleft = (0, idx * (self.font_small.get_height() + 2))
			surfaces.append((surf, rect))
			max_width = max(max_width, rect.width)
		height = surfaces[-1][1].bottom if surfaces else 0
		tooltip_rect = pygame.Rect(0, 0, max_width + padding * 2, height + padding * 2)
		tooltip_rect.topleft = (mouse_x + 24, mouse_y + 24)
		if tooltip_rect.right > WIDTH - 10:
			tooltip_rect.right = mouse_x - 24
		if tooltip_rect.bottom > HEIGHT - 10:
			tooltip_rect.bottom = HEIGHT - 10
		pygame.draw.rect(self.screen, TOOLTIP_BG, tooltip_rect, border_radius=10)
		pygame.draw.rect(self.screen, TOOLTIP_BORDER, tooltip_rect, 2, border_radius=10)
		for surf, rect in surfaces:
			rect.topleft = (tooltip_rect.x + padding, tooltip_rect.y + padding + rect.y)
			self.screen.blit(surf, rect)

	def draw_turbo_pipes(self) -> None:
		if not self.turbo_pipes:
			return
		for turbo in self.turbo_pipes:
			if not turbo.positions:
				turbo.positions = self.build_turbo_positions(turbo.start_progress, turbo.end_progress)
			if len(turbo.positions) < 2:
				continue
			pygame.draw.lines(self.screen, TURBO_PIPE_COLOR, False, turbo.positions, 8)
			start_x, start_y = turbo.positions[0]
			end_x, end_y = turbo.positions[-1]
			pygame.draw.circle(self.screen, TURBO_PIPE_COLOR, (int(start_x), int(start_y)), 6)
			pygame.draw.circle(self.screen, TURBO_PIPE_COLOR, (int(end_x), int(end_y)), 6)

	def draw_portals(self) -> None:
		if not self.portals:
			return
		state = self.portal_state
		for portal in self.portals:
			cx, cy = portal.center
			radius = portal.radius
			if state == "active":
				color = PORTAL_GLOW_COLOR
			elif state == "cooldown":
				color = (230, 190, 110)
			else:
				color = (70, 90, 130)
			outer_rect = pygame.Rect(0, 0, radius * 2, radius * 2)
			outer_rect.center = (cx, cy)
			pygame.draw.ellipse(self.screen, PORTAL_BASE_COLOR, outer_rect.inflate(10, 24), 2)
			pygame.draw.circle(self.screen, color, (cx, cy), radius, width=3)
			inner_radius = max(6, radius - 6)
			pygame.draw.circle(self.screen, color, (cx, cy), inner_radius, width=1)

	def draw_bouncers(self) -> None:
		if not self.bouncers:
			return
		for bouncer in self.bouncers:
			remaining = max(0, bouncer.removals_remaining)
			cx, cy = bouncer.center
			radius = bouncer.radius
			outer_rect = pygame.Rect(0, 0, radius * 2, radius * 2)
			outer_rect.center = (cx, cy)
			ready = bouncer.ready_to_drop or remaining == 0
			base_color = (90, 200, 180) if ready else (35, 45, 70)
			inner_color = (255, 245, 180) if ready else (140, 210, 255)
			pygame.draw.circle(self.screen, base_color, (cx, cy), radius, width=3)
			pygame.draw.circle(self.screen, inner_color, (cx, cy), max(6, radius - 8), width=2)
			text_value = str(remaining)
			text_surface = self.font_small.render(text_value, True, (255, 255, 255))
			text_rect = text_surface.get_rect(center=(cx, cy))
			self.screen.blit(text_surface, text_rect)

	def draw_storm_emitters(self) -> None:
		if not self.storm_emitters:
			return
		now = pygame.time.get_ticks()
		for emitter in self.storm_emitters:
			cx, cy = emitter.center
			radius = emitter.radius
			pygame.draw.circle(self.screen, (120, 80, 180), (cx, cy), radius, width=3)
			pygame.draw.circle(self.screen, (220, 200, 255), (cx, cy), max(6, radius - 10), width=2)
			pygame.draw.circle(self.screen, (255, 255, 255), (cx, cy), 4)
			if emitter.settle_at and now < emitter.settle_at:
				remain = max(0.0, (emitter.settle_at - now) / 1000.0)
				status_text = self.font_small.render(f"{remain:0.1f}s", True, (230, 220, 255))
				status_rect = status_text.get_rect(center=(cx, cy - radius - 18))
				self.screen.blit(status_text, status_rect)
				count_text = self.font_small.render(f"Eggs {emitter.window_count}", True, (200, 190, 230))
				count_rect = count_text.get_rect(center=(cx, cy + radius + 12))
				self.screen.blit(count_text, count_rect)
			if emitter.animation_until > now:
				remaining = max(0, emitter.animation_until - now)
				elapsed = STORM_ANIMATION_DURATION - remaining
				phase = max(0.0, min(1.0, elapsed / max(1, STORM_ANIMATION_DURATION)))
				for scale in (1.2, 1.5, 1.8):
					pulse = int(radius * (scale + phase * 0.5))
					alpha = max(0, 200 - int(phase * 180) - int((scale - 1.0) * 60))
					if alpha <= 0 or pulse <= 0:
						continue
					surface = pygame.Surface((pulse * 2, pulse * 2), pygame.SRCALPHA)
					pygame.draw.circle(surface, (255, 200, 120, alpha), (pulse, pulse), pulse, width=3)
					self.screen.blit(surface, (cx - pulse, cy - pulse))
				reward = emitter.last_reward
				if reward > 0:
					display_value = max(1, int(reward * phase)) if phase < 1.0 else reward
					alpha = max(40, 255 - int(phase * 255))
					scale = 1.0 + 0.4 * (1.0 - phase)
					label = f"+{display_value}"
					text = self.font_large.render(label, True, (255, 255, 255))
					text = pygame.transform.rotozoom(text, 0, scale)
					surface = pygame.Surface(text.get_size(), pygame.SRCALPHA)
					surface.blit(text, (0, 0))
					surface.set_alpha(alpha)
					rect = surface.get_rect(center=(cx, cy - radius - 12))
					self.screen.blit(surface, rect)
					if emitter.counted_eggs:
						count_label = self.font_small.render(
							f"{emitter.counted_eggs} eggs", True, (255, 240, 255)
						)
						count_rect = count_label.get_rect(center=(cx, cy + radius + 16))
						self.screen.blit(count_label, count_rect)

	def run(self) -> None:
		running = True
		while running:
			dt = self.clock.tick(60) / 1000.0
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					running = False
				elif event.type == pygame.KEYDOWN:
					if event.key == pygame.K_ESCAPE:
						running = False
					elif event.key == pygame.K_RETURN and self.round_result == "success":
						next_level = self.current_level + 1 if self.current_level < self.max_level else 1
						carry_layout = next_level > self.current_level
						self.reset_round(next_level, carry_items=carry_layout)
					elif not self.round_active:
						if event.key == pygame.K_SPACE and self.round_result == "fail":
							self.reset_round(1)
						elif event.key == pygame.K_r:
							self.reset_round(1)
				elif event.type == pygame.MOUSEBUTTONDOWN:
					if event.button == 1:
						self.handle_click(event.pos)
					elif event.button == 3:
						self.handle_right_click(event.pos)

			remaining = self.remaining_time()
			self.update(dt)

			self.screen.fill(BG_COLOR)
			self.draw_shop()
			self.draw_power_bar()
			self.draw_track()
			self.draw_machine()
			self.draw_balls()
			self.draw_coin_popups()
			self.draw_panel(remaining)
			self.draw_footer(remaining)
			self.draw_skill_overlay()
			self.draw_shop_tooltip()

			pygame.display.flip()

		pygame.quit()

	def handle_click(self, pos: Tuple[int, int]) -> None:
		if self.current_level >= PASSIVE_UNLOCK_LEVEL and self.skill_selection_required:
			self.handle_skill_selection_click(pos)
			return
		if self.handle_skill_selection_click(pos):
			return
		if self.pipe_button.collidepoint(pos):
			self.try_purchase_pipe()
			return
		if self.blocks_enabled() and self.block_button.collidepoint(pos):
			self.try_purchase_block()
			return
		if self.portal_enabled() and self.portal_button.collidepoint(pos):
			self.try_purchase_portal()
			return
		if self.turbo_enabled() and self.turbo_button.collidepoint(pos):
			self.try_purchase_turbo_pipe()
			return
		if self.storm_ui_visible() and self.storm_button.collidepoint(pos):
			self.try_purchase_storm()
			return
		if self.speed_boost_ui_visible() and self.speed_boost_button.collidepoint(pos):
			self.try_activate_speed_boost()
			return
		if self.bouncepad_ui_visible() and self.bouncepad_button.collidepoint(pos):
			self.try_activate_bouncepad()
			return
		play_min = SHOP_WIDTH + 20
		play_max = WIDTH - UTILITY_WIDTH - 20
		if self.placing_pipe and play_min < pos[0] < play_max:
			self.place_pipe(pos)
		elif self.placing_block and play_min < pos[0] < play_max:
			if self.try_upgrade_block(pos):
				return
			self.place_block(pos)
		elif self.placing_turbo_pipe and play_min < pos[0] < play_max:
			self.place_turbo_pipe(pos)
		elif self.placing_bouncer and play_min < pos[0] < play_max:
			self.place_bouncer(pos)
		elif self.placing_storm and play_min < pos[0] < play_max:
			self.place_storm(pos)
		elif self.placing_portal and play_min < pos[0] < play_max:
			self.place_portal(pos)

	def try_purchase_pipe(self) -> None:
		if (
			self.placing_pipe
			or self.placing_block
			or self.placing_turbo_pipe
			or self.placing_bouncer
			or self.placing_storm
			or self.placing_portal
		):
			return
		cost = self.next_pipe_cost()
		if self.coins < cost:
			return
		self.coins -= cost
		self.pipe_counter += 1
		self.pipe_purchases += 1
		self.placing_pipe = PipeItem(id=self.pipe_counter, cost=cost)

	def try_purchase_block(self) -> None:
		if not self.blocks_enabled():
			return
		if (
			self.placing_block
			or self.placing_pipe
			or self.placing_turbo_pipe
			or self.placing_bouncer
			or self.placing_storm
			or self.placing_portal
		):
			return
		cost = self.next_block_cost()
		if self.coins < cost:
			return
		self.coins -= cost
		self.block_counter += 1
		self.block_purchases += 1
		self.placing_block = BlockItem(id=self.block_counter, cost=cost)

	def try_purchase_turbo_pipe(self) -> None:
		if not self.turbo_enabled():
			return
		if (
			self.placing_turbo_pipe
			or self.placing_pipe
			or self.placing_block
			or self.placing_bouncer
			or self.placing_storm
			or self.placing_portal
		):
			return
		cost = self.next_turbo_cost()
		if self.coins < cost:
			return
		self.coins -= cost
		self.turbo_counter += 1
		self.turbo_purchases += 1
		self.placing_turbo_pipe = TurboPipeItem(id=self.turbo_counter, cost=cost)

	def try_activate_bouncepad(self) -> None:
		if not self.bouncer_enabled():
			return
		if self.placing_bouncer:
			return
		if self.bouncepad_charges <= 0:
			return
		if (
			self.placing_pipe
			or self.placing_block
			or self.placing_turbo_pipe
			or self.placing_portal
			or self.placing_storm
		):
			return
		self.bouncepad_charges = max(0, self.bouncepad_charges - 1)
		self.bouncer_counter += 1
		self.bouncer_purchases += 1
		self.placing_bouncer = BouncerItem(id=self.bouncer_counter, cost=0)

	def try_purchase_portal(self) -> None:
		if not self.portal_enabled():
			return
		if self.placing_portal:
			return
		if (
			self.placing_pipe
			or self.placing_block
			or self.placing_turbo_pipe
			or self.placing_bouncer
			or self.placing_storm
		):
			return
		if len(self.portals) >= 2 and self.portal_state != "cooldown":
			return
		cost = self.next_portal_cost()
		if self.coins < cost:
			return
		self.coins -= cost
		self.portal_counter += 1
		self.portal_purchases += 1
		self.placing_portal = PortalItem(id=self.portal_counter, cost=cost)

	def try_purchase_storm(self) -> None:
		if not self.storm_enabled():
			return
		if self.placing_storm:
			return
		if self.storm_charges <= 0:
			return
		if (
			self.placing_pipe
			or self.placing_block
			or self.placing_turbo_pipe
			or self.placing_bouncer
			or self.placing_portal
		):
			return
		self.storm_counter += 1
		cost = self.next_storm_cost()
		self.storm_charges = max(0, self.storm_charges - 1)
		self.placing_storm = StormItem(id=self.storm_counter, cost=cost)

	def handle_right_click(self, pos: Tuple[int, int]) -> None:
		if self.current_level >= PASSIVE_UNLOCK_LEVEL and self.skill_selection_required:
			return
		if not (SHOP_WIDTH + 20 < pos[0] < WIDTH - UTILITY_WIDTH - 20):
			return
		if self.try_remove_item_at(pos):
			self.coins += REMOVAL_BONUS
			self.add_coin_popup(pos, f"+{REMOVAL_BONUS}")

	def try_remove_item_at(self, pos: Tuple[int, int]) -> bool:
		removers = (
			("pipe", self.remove_pipe_at),
			("block", self.remove_block_at),
			("turbo", self.remove_turbo_pipe_at),
			("bouncer", self.remove_bouncer_at),
			("storm", self.remove_storm_at),
			("portal", self.remove_portal_at),
		)
		for kind, remover in removers:
			if remover(pos):
				if kind != "bouncer":
					self.handle_tool_removed(kind)
				return True
		return False

	def remove_pipe_at(self, pos: Tuple[int, int]) -> bool:
		if not self.pipes:
			return False
		for pipe in reversed(self.pipes):
			if not pipe.rect:
				continue
			inflated = pipe.rect.inflate(20, 20)
			if inflated.collidepoint(pos):
				self.pipes.remove(pipe)
				return True
		return False

	def remove_block_at(self, pos: Tuple[int, int]) -> bool:
		if not self.blocks:
			return False
		px, py = pos
		for block in reversed(self.blocks):
			x, y = block.pos
			if math.hypot(px - x, py - y) <= block.radius + 12:
				self.blocks.remove(block)
				return True
		return False

	def remove_turbo_pipe_at(self, pos: Tuple[int, int]) -> bool:
		if not self.turbo_pipes:
			return False
		for turbo in reversed(self.turbo_pipes):
			if not turbo.positions:
				turbo.positions = self.build_turbo_positions(turbo.start_progress, turbo.end_progress)
			distance = self.polyline_distance(turbo.positions, pos)
			if distance <= 18:
				self.turbo_pipes.remove(turbo)
				return True
		return False

	def remove_bouncer_at(self, pos: Tuple[int, int]) -> bool:
		if not self.bouncers:
			return False
		px, py = pos
		for bouncer in reversed(self.bouncers):
			x, y = bouncer.center
			if math.hypot(px - x, py - y) <= bouncer.radius + 12:
				self.bouncers.remove(bouncer)
				return True
		return False

	def remove_storm_at(self, pos: Tuple[int, int]) -> bool:
		if not self.storm_emitters:
			return False
		px, py = pos
		for emitter in reversed(self.storm_emitters):
			x, y = emitter.center
			if math.hypot(px - x, py - y) <= emitter.radius + 12:
				self.storm_emitters.remove(emitter)
				return True
		return False

	def remove_portal_at(self, pos: Tuple[int, int]) -> bool:
		if not self.portals:
			return False
		px, py = pos
		for portal in reversed(self.portals):
			x, y = portal.center
			if math.hypot(px - x, py - y) <= portal.radius + 12:
				self.portals.remove(portal)
				self.portal_state = "inactive"
				self.portal_active_until = 0
				self.portal_cooldown_until = 0
				return True
		return False

	def place_pipe(self, pos: Tuple[int, int]) -> None:
		if not self.placing_pipe:
			return
		x = max(SHOP_WIDTH + 80, min(WIDTH - UTILITY_WIDTH - 80, pos[0]))
		intersections = self.track_intersections_at_x(x)
		if len(intersections) < 2:
			up = max(120, pos[1] - PIPE_HEIGHT // 2)
			up = min(HEIGHT - PIPE_HEIGHT - 60, up)
			rect = pygame.Rect(0, 0, 26, PIPE_HEIGHT)
			rect.center = (x, up + PIPE_HEIGHT // 2)
			entry_prog, exit_prog = self.pipe_progress_from_rect(rect)
			entry_y = rect.top + 10
			exit_y = rect.bottom - 10
		else:
			pair = self.pick_intersection_pair(intersections, pos[1])
			top = intersections[pair[0]]
			bottom = intersections[pair[1]]
			top_y, top_prog, _ = top
			bottom_y, bottom_prog, _ = bottom
			height = max(20, bottom_y - top_y)
			rect = pygame.Rect(0, 0, 26, height)
			rect.midtop = (x, top_y)
			entry_prog, exit_prog = top_prog, bottom_prog
			entry_y, exit_y = top_y, bottom_y
		start_node, end_node = self.snap_progress_span(entry_prog, exit_prog)
		_, entry_y, entry_prog = start_node
		_, exit_y, exit_prog = end_node
		pipe = self.placing_pipe
		pipe_width = rect.width
		pipe_x = rect.centerx
		visual_top = min(entry_y, exit_y)
		visual_height = max(20, abs(exit_y - entry_y) + 20)
		snapped_rect = pygame.Rect(0, 0, pipe_width, int(visual_height))
		snapped_rect.midtop = (int(pipe_x), int(visual_top))
		pipe.rect = snapped_rect
		pipe.entry_progress = entry_prog
		pipe.exit_progress = exit_prog
		pipe.entry_y = entry_y
		pipe.exit_y = exit_y
		pipe.x = pipe_x
		self.pipes.append(pipe)
		self.pipes.sort(key=lambda item: item.entry_progress)
		self.placing_pipe = None

	def place_block(self, pos: Tuple[int, int]) -> None:
		if not self.placing_block:
			return
		x, y, progress = self.nearest_point_on_track(pos)
		x, y, progress = self.snap_progress_point(progress)
		if self.track_point_occupied(progress):
			return
		block = self.placing_block
		block.pos = (x, y)
		block.progress = progress
		now = pygame.time.get_ticks()
		self.activate_block(block, now)
		self.blocks.append(block)
		self.placing_block = None

	def activate_block(self, block: BlockItem, now: int) -> None:
		block.is_active = True
		block.spawn_ms = now
		block.active_until_ms = now + int(block.active_duration * 1000)
		block.cooldown_start_ms = 0
		block.cooldown_end_ms = 0

	def begin_block_cooldown(self, block: BlockItem, now: int) -> None:
		block.is_active = False
		block.cooldown_start_ms = now
		block.cooldown_end_ms = now + int(block.cooldown_duration * 1000)
		if block.cooldown_duration <= 0.0:
			self.activate_block(block, now)

	def block_at_position(self, pos: Tuple[int, int]) -> Optional[BlockItem]:
		px, py = pos
		for block in reversed(self.blocks):
			x, y = block.pos
			if math.hypot(px - x, py - y) <= block.radius + 12:
				return block
		return None

	def try_upgrade_block(self, pos: Tuple[int, int]) -> bool:
		if not self.blocks:
			return False
		target = self.block_at_position(pos)
		if not target:
			return False
		self.apply_block_upgrade(target)
		self.placing_block = None
		return True

	def apply_block_upgrade(self, block: BlockItem) -> None:
		"""Consume a purchased block to refresh an installed one."""
		now = pygame.time.get_ticks()
		block.active_duration = max(block.active_duration, BLOCK_UPGRADED_DURATION)
		if block.is_active:
			block.active_until_ms = block.spawn_ms + int(block.active_duration * 1000)
		reduction_idx = block.upgrade_count
		if reduction_idx < len(BLOCK_COOLDOWN_REDUCTION_STEPS):
			reduction = BLOCK_COOLDOWN_REDUCTION_STEPS[reduction_idx]
		else:
			reduction = BLOCK_COOLDOWN_REDUCTION_STEPS[-1]
		block.cooldown_duration = max(0.0, block.cooldown_duration - reduction)
		block.upgrade_count += 1
		if not block.is_active:
			block.cooldown_end_ms = block.cooldown_start_ms + int(block.cooldown_duration * 1000)
			if block.cooldown_end_ms <= now:
				self.activate_block(block, now)

	def place_turbo_pipe(self, pos: Tuple[int, int]) -> None:
		if not self.placing_turbo_pipe:
			return
		_, _, progress = self.nearest_point_on_track(pos)
		length = self.placing_turbo_pipe.length_progress
		start_prog = max(0.0, progress - length / 2)
		end_prog = min(1.0, progress + length / 2)
		if end_prog - start_prog < length:
			missing = length - (end_prog - start_prog)
			start_prog = max(0.0, start_prog - missing / 2)
			end_prog = min(1.0, end_prog + missing / 2)
		start_node, end_node = self.snap_progress_span(start_prog, end_prog)
		start_prog = start_node[2]
		end_prog = end_node[2]
		if self.track_span_occupied(start_prog, end_prog):
			return
		turbo = self.placing_turbo_pipe
		turbo.start_progress = start_prog
		turbo.end_progress = end_prog
		turbo.positions = self.build_turbo_positions(start_prog, end_prog)
		self.turbo_pipes.append(turbo)
		self.turbo_pipes.sort(key=lambda item: item.start_progress)
		self.placing_turbo_pipe = None

	def place_bouncer(self, pos: Tuple[int, int]) -> None:
		if not self.placing_bouncer:
			return
		x, y, progress = self.nearest_point_on_track(pos)
		x, y, progress = self.snap_progress_point(progress)
		if self.track_point_occupied(progress):
			return
		bouncer = self.placing_bouncer
		bouncer.center = (int(x), int(y))
		bouncer.progress = progress
		bouncer.removals_remaining = BOUNCER_TRIGGER_REMOVALS
		bouncer.ready_to_drop = False
		self.bouncers.append(bouncer)
		self.placing_bouncer = None
		self.update_bouncer_supply()

	def place_storm(self, pos: Tuple[int, int]) -> None:
		if not self.placing_storm:
			return
		x, y, progress = self.nearest_point_on_track(pos)
		x, y, progress = self.snap_progress_point(progress)
		if self.track_point_occupied(progress):
			return
		storm = self.placing_storm
		storm.center = (int(x), int(y))
		storm.progress = progress
		now_ms = pygame.time.get_ticks()
		storm.window_count = 0
		storm.counted_eggs = 0
		storm.animation_until = 0
		storm.last_reward = 0
		storm.settle_at = now_ms + STORM_WINDOW_DURATION
		storm.expires_at = now_ms + STORM_LIFETIME_MS
		self.storm_emitters.append(storm)
		self.placing_storm = None

	def place_portal(self, pos: Tuple[int, int]) -> None:
		if not self.placing_portal:
			return
		x, y, progress = self.nearest_point_on_track(pos)
		x, y, progress = self.snap_progress_point(progress)
		target_point = (int(x), int(y))
		if self.portal_state == "cooldown" and len(self.portals) >= 2:
			if self.try_accelerate_portal_cooldown(target_point):
				self.placing_portal = None
			return
		if self.track_point_occupied(progress):
			return
		portal = self.placing_portal
		portal.center = target_point
		portal.progress = progress
		self.portals.append(portal)
		self.portals.sort(key=lambda item: item.progress)
		self.placing_portal = None
		if len(self.portals) > 2:
			self.portals = self.portals[-2:]
			self.portals.sort(key=lambda item: item.progress)
		self.portal_state = "inactive"
		self.portal_active_until = 0
		self.portal_cooldown_until = 0

	def ball_progress(self, ball: Ball) -> float:
		if self.track_total <= 0:
			return 0.0
		return min(ball.distance / self.track_total, 1.0)

	def progress_to_distance(self, progress: float) -> float:
		progress = max(0.0, min(progress, 1.0))
		return progress * self.track_total

	def pipe_progress_from_rect(self, rect: pygame.Rect) -> Tuple[float, float]:
		entry_y = rect.top + 10
		exit_y = rect.bottom - 10
		entry_prog = self.progress_from_y(entry_y)
		exit_prog = self.progress_from_y(exit_y)
		if exit_prog <= entry_prog:
			exit_prog = min(1.0, entry_prog + 0.1)
		return entry_prog, exit_prog

	def track_intersections_at_x(self, target_x: float) -> List[Tuple[float, float, Tuple[float, float]]]:
		intersections: List[Tuple[float, float, Tuple[float, float]]] = []
		for i in range(len(self.track_points) - 1):
			x1, y1 = self.track_points[i]
			x2, y2 = self.track_points[i + 1]
			dx = x2 - x1
			if abs(dx) < 1e-5:
				continue
			if not (min(x1, x2) <= target_x <= max(x1, x2)):
				continue
			t = (target_x - x1) / dx
			if not (0.0 <= t <= 1.0):
				continue
			y = y1 + (y2 - y1) * t
			seg_len = math.hypot(dx, y2 - y1)
			seg_prog = (self.track_lengths[i] + seg_len * t) / self.track_total
			intersections.append((y, seg_prog, (target_x, y)))
		intersections.sort(key=lambda item: item[0])
		return intersections

	def pick_intersection_pair(
		self, intersections: List[Tuple[float, float, Tuple[float, float]]], click_y: float
	) -> Tuple[int, int]:
		if len(intersections) < 2:
			return 0, 0
		for idx in range(len(intersections) - 1):
			top_y = intersections[idx][0]
			bottom_y = intersections[idx + 1][0]
			if top_y <= click_y <= bottom_y:
				return idx, idx + 1
		best = 0
		best_dist = float("inf")
		for idx in range(len(intersections) - 1):
			mid = 0.5 * (intersections[idx][0] + intersections[idx + 1][0])
			dist = abs(mid - click_y)
			if dist < best_dist:
				best = idx
				best_dist = dist
		return best, min(best + 1, len(intersections) - 1)

	def progress_from_y(self, target_y: float) -> float:
		nearest_idx = min(
			range(len(self.track_points)),
			key=lambda i: abs(self.track_points[i][1] - target_y),
		)
		return self.track_lengths[nearest_idx] / self.track_total

	def nearest_point_on_track(self, pos: Tuple[int, int]) -> Tuple[float, float, float]:
		px, py = pos
		best_point = self.track_points[0]
		best_progress = 0.0
		best_dist = float("inf")
		for i in range(len(self.track_points) - 1):
			x1, y1 = self.track_points[i]
			x2, y2 = self.track_points[i + 1]
			dx, dy = x2 - x1, y2 - y1
			seg_len_sq = dx * dx + dy * dy
			if seg_len_sq < 1e-6:
				continue
			t = ((px - x1) * dx + (py - y1) * dy) / seg_len_sq
			t = max(0.0, min(1.0, t))
			proj_x = x1 + dx * t
			proj_y = y1 + dy * t
			dist = math.hypot(proj_x - px, proj_y - py)
			if dist < best_dist:
				best_dist = dist
				best_point = (proj_x, proj_y)
				seg_len = math.sqrt(seg_len_sq)
				path_dist = self.track_lengths[i] + seg_len * t
				best_progress = path_dist / self.track_total if self.track_total else 0.0
		return best_point[0], best_point[1], best_progress

	def build_track_nodes(self, count: int) -> List[Tuple[float, float, float]]:
		nodes: List[Tuple[float, float, float]] = []
		if self.track_total <= 0 or count <= 1:
			x, y = self.track_points[0]
			nodes.append((x, y, 0.0))
			return nodes
		for idx in range(count):
			progress = idx / (count - 1)
			x, y = lerp_point(self.track_points, self.track_lengths, self.track_total, progress)
			nodes.append((x, y, progress))
		return nodes

	def closest_track_node_index(self, progress: float) -> int:
		if not getattr(self, "track_node_progress", None):
			return 0
		progress = max(0.0, min(progress, 1.0))
		idx = bisect_left(self.track_node_progress, progress)
		if idx >= len(self.track_node_progress):
			idx = len(self.track_node_progress) - 1
		elif idx > 0:
			prev_prog = self.track_node_progress[idx - 1]
			curr_prog = self.track_node_progress[idx]
			if abs(progress - prev_prog) <= abs(curr_prog - progress):
				idx -= 1
		return idx

	def snap_progress_point(self, progress: float) -> Tuple[float, float, float]:
		if not self.track_nodes:
			x, y = self.track_points[0]
			return x, y, 0.0
		idx = self.closest_track_node_index(progress)
		x, y, snapped = self.track_nodes[idx]
		return x, y, snapped

	def track_point_occupied(self, progress: float) -> bool:
		"""Return True when any placed tool already uses this snapped track progress."""
		return self.track_span_occupied(progress, progress)

	def track_span_occupied(self, start_prog: float, end_prog: float) -> bool:
		start = max(0.0, min(start_prog, end_prog)) - TRACK_POINT_TOLERANCE
		end = min(1.0, max(start_prog, end_prog)) + TRACK_POINT_TOLERANCE
		start = max(0.0, start)
		end = min(1.0, end)
		def span_contains(value: float) -> bool:
			return start <= value <= end
		for block in self.blocks:
			if span_contains(block.progress):
				return True
		for bouncer in self.bouncers:
			if span_contains(bouncer.progress):
				return True
		for storm in self.storm_emitters:
			if span_contains(storm.progress):
				return True
		for portal in self.portals:
			if span_contains(portal.progress):
				return True
		for turbo in self.turbo_pipes:
			turbo_start = min(turbo.start_progress, turbo.end_progress)
			turbo_end = max(turbo.start_progress, turbo.end_progress)
			if turbo_start <= end and turbo_end >= start:
				return True
		return False

	def snap_progress_span(
		self,
		start_prog: float,
		end_prog: float,
	) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
		if not self.track_nodes:
			first = (self.track_points[0][0], self.track_points[0][1], 0.0)
			last = (self.track_points[-1][0], self.track_points[-1][1], 1.0)
			return first, last
		start_idx = self.closest_track_node_index(start_prog)
		end_idx = self.closest_track_node_index(end_prog)
		if start_idx == end_idx:
			if end_idx < len(self.track_nodes) - 1:
				end_idx += 1
			elif start_idx > 0:
				start_idx -= 1
		if start_idx > end_idx:
			start_idx, end_idx = end_idx, start_idx
		return self.track_nodes[start_idx], self.track_nodes[end_idx]

	def point_segment_distance(
		self,
		px: float,
		py: float,
		ax: float,
		ay: float,
		bx: float,
		by: float,
	) -> float:
		dx = bx - ax
		dy = by - ay
		if abs(dx) < 1e-6 and abs(dy) < 1e-6:
			return math.hypot(px - ax, py - ay)
		t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
		t = max(0.0, min(1.0, t))
		closest_x = ax + dx * t
		closest_y = ay + dy * t
		return math.hypot(px - closest_x, py - closest_y)

	def polyline_distance(self, points: Sequence[Tuple[float, float]], pos: Tuple[int, int]) -> float:
		if len(points) < 2:
			return float("inf")
		px, py = pos
		best = float("inf")
		for i in range(len(points) - 1):
			ax, ay = points[i]
			bx, by = points[i + 1]
			best = min(best, self.point_segment_distance(px, py, ax, ay, bx, by))
		return best

	def build_turbo_positions(self, start_progress: float, end_progress: float, samples: int = 16) -> List[Tuple[float, float]]:
		if end_progress <= start_progress:
			return []
		positions: List[Tuple[float, float]] = []
		for idx in range(samples + 1):
			ratio = idx / samples
			prog = start_progress + (end_progress - start_progress) * ratio
			positions.append(
				lerp_point(self.track_points, self.track_lengths, self.track_total, prog)
			)
		return positions

	def update_blocks(self) -> None:
		if not self.blocks:
			return
		now = pygame.time.get_ticks()
		for block in self.blocks:
			if block.is_active:
				if block.active_until_ms == 0:
					block.active_until_ms = block.spawn_ms + int(block.active_duration * 1000)
				if now >= block.active_until_ms:
					self.begin_block_cooldown(block, now)
			else:
				cooldown_ready = block.cooldown_end_ms == 0 or now >= block.cooldown_end_ms
				if block.cooldown_duration <= 0.0 or cooldown_ready:
					self.activate_block(block, now)

	def update_bouncer_supply(self) -> None:
		if not self.bouncers:
			return
		triggered = [b for b in list(self.bouncers) if b.ready_to_drop or b.removals_remaining <= 0]
		for bouncer in triggered:
			if bouncer in self.bouncers:
				self.bouncers.remove(bouncer)
			self.spawn_bouncer_drops(bouncer)

	def spawn_bouncer_drops(self, bouncer: BouncerItem) -> None:
		drop_options = [
			kind for kind in self.collectible_powerup_types() if kind != BOUNCEPAD_POWERUP_KIND
		]
		if not drop_options:
			drop_options = ["speed_boost"]
		count = random.randint(BOUNCER_DROP_MIN, BOUNCER_DROP_MAX)
		for _ in range(count):
			offset = random.uniform(-BOUNCER_DROP_SPREAD, BOUNCER_DROP_SPREAD)
			progress = min(max(bouncer.progress + offset, 0.0), 1.0)
			x, y = lerp_point(
				self.track_points,
				self.track_lengths,
				self.track_total,
				progress,
			)
			self.powerup_counter += 1
			kind = random.choice(drop_options)
			self.track_powerups.append(
				TrackPowerup(
					id=self.powerup_counter,
					kind=kind,
					progress=progress,
					pos=(int(x), int(y)),
				)
			)
		self.add_coin_popup(bouncer.center, f"{count} drops")

	def apply_skill_income(self, dt: float) -> None:
		if "coin_rain" not in self.active_skills or not self.round_active:
			return
		self.skill_coin_timer += dt
		while self.skill_coin_timer >= 1.0:
			self.coins += COIN_RAIN_RATE
			self.skill_coin_timer -= 1.0

	def apply_rapid_fire(self, dt: float) -> None:
		if "rapid_fire" not in self.active_skills or not self.round_active:
			return
		if self.round_start_ms is None:
			return
		self.rapid_fire_timer += dt
		while self.rapid_fire_timer >= RAPID_FIRE_INTERVAL:
			self.spawn_ball()
			self.rapid_fire_timer -= RAPID_FIRE_INTERVAL

	def apply_pipe(self, ball: Ball, dt: float) -> bool:
		if not self.pipes:
			return False
		multiplier = self.speed_boost_multiplier()
		if ball.in_pipe:
			pipe = self.get_pipe_by_id(ball.pipe_id)
			if not pipe or not pipe.rect:
				ball.in_pipe = False
				ball.pipe_id = None
				return False
			exit_y = pipe.exit_y or (pipe.rect.bottom - 10)
			ball.pipe_y += PIPE_SPEED * multiplier * dt
			if ball.pipe_y >= exit_y:
				ball.pipe_y = exit_y
				ball.in_pipe = False
				ball.pipe_id = None
				ball.used_pipes.add(pipe.id)
				exit_distance = self.progress_to_distance(pipe.exit_progress)
				ball.distance = max(ball.distance, exit_distance)
				ball.last_distance = ball.distance
			return True
		for pipe in self.pipes:
			if pipe.id in ball.used_pipes or not pipe.rect:
				continue
			entry_distance = self.progress_to_distance(pipe.entry_progress)
			if ball.last_distance < entry_distance <= ball.distance:
				ball.in_pipe = True
				ball.pipe_id = pipe.id
				entry_y = pipe.entry_y or (pipe.rect.top + 10)
				ball.pipe_y = entry_y
				ball.pipe_x = pipe.x or pipe.rect.centerx
				ball.speed = 0.0
				ball.distance = max(ball.distance, entry_distance)
				ball.last_distance = ball.distance
				return True
		return False

	def apply_block_effects(self, ball: Ball) -> None:
		if not self.blocks:
			return
		for block in self.blocks:
			if not block.is_active:
				continue
			if block.id in ball.block_hits:
				continue
			block_distance = self.progress_to_distance(block.progress)
			if ball.last_distance < block_distance <= ball.distance:
				ball.speed = max(ball.speed * BLOCK_SLOW_FACTOR, 0.0)
				ball.block_hits.add(block.id)
				ball.bonus_score += BLOCK_BONUS

	def apply_turbo_effects(self, ball: Ball, dt: float, speed_multiplier: float) -> None:
		if not self.turbo_pipes:
			return
		zone_multiplier = 1.0
		for turbo in self.turbo_pipes:
			start_distance = self.progress_to_distance(turbo.start_progress)
			end_distance = self.progress_to_distance(turbo.end_progress)
			if ball.last_distance < end_distance and ball.distance > start_distance:
				zone_multiplier = max(zone_multiplier, TURBO_PIPE_MULTIPLIER)
				if turbo.id not in ball.turbo_hits and ball.last_distance <= start_distance:
					previous_value = ball.score_value
					ball.score_value *= 2
					self.show_turbo_bonus_popup(ball, ball.score_value - previous_value)
					ball.speed = min(
						ball.speed * TURBO_PIPE_MULTIPLIER,
						BALL_MAX_SPEED * TURBO_PIPE_MULTIPLIER,
					)
					ball.turbo_hits.add(turbo.id)
		if zone_multiplier > 1.0:
			extra = (ball.speed * speed_multiplier) * dt * (zone_multiplier - 1.0)
			ball.distance += extra
		else:
			ball.speed = min(ball.speed, BALL_MAX_SPEED)

	def apply_portal_effects(self, ball: Ball) -> None:
		if len(self.portals) < 2:
			return
		if self.portal_state != "active":
			return
		if ball.in_pipe:
			return
		ordered = sorted(
			self.portals[:2],
			key=lambda item: item.center[1],
			reverse=True,
		)
		entry_portal, exit_portal = ordered[0], ordered[1]
		entry_distance = self.progress_to_distance(entry_portal.progress)
		exit_distance = self.progress_to_distance(exit_portal.progress)
		if not (ball.last_distance < entry_distance <= ball.distance):
			return
		teleport_distance = exit_distance + BALL_RADIUS * 1.5
		ball.distance = teleport_distance
		ball.last_distance = ball.distance
		ball.speed = max(ball.speed, BALL_ACCEL * 0.1)

	def process_storm_pass(self, ball: Ball) -> None:
		if not self.storm_emitters:
			return
		now = pygame.time.get_ticks()
		for storm in self.storm_emitters:
			if not storm.settle_at:
				continue
			if now > storm.settle_at:
				continue
			impact_distance = self.progress_to_distance(storm.progress)
			if not (ball.last_distance < impact_distance <= ball.distance):
				continue
			storm.window_count += 1

	def trigger_storm(self, storm: StormItem) -> None:
		if storm.last_reward > 0:
			return
		now = pygame.time.get_ticks()
		storm.counted_eggs = max(storm.counted_eggs, storm.window_count)
		progress = min(1.0, storm.counted_eggs / max(1, STORM_WINDOW_TARGET))
		max_reward = STORM_MIN_EGGS + int((STORM_MAX_EGGS - STORM_MIN_EGGS) * progress)
		max_reward = max(STORM_MIN_EGGS, min(STORM_MAX_EGGS, max_reward))
		reward = random.randint(STORM_MIN_EGGS, max_reward)
		storm.last_reward = reward
		storm.animation_until = now + STORM_ANIMATION_DURATION
		storm.expires_at = storm.animation_until
		storm.window_count = 0
		storm.settle_at = 0
		if self.round_active:
			self.score += reward
			self.coins += reward
			self.check_round_victory()

	def activate_portals(self, now: Optional[int] = None) -> None:
		if len(self.portals) < 2:
			self.portal_state = "inactive"
			self.portal_active_until = 0
			self.portal_cooldown_until = 0
			return
		if now is None:
			now = pygame.time.get_ticks()
		self.portal_state = "active"
		self.portal_active_until = now + int(PORTAL_ACTIVE_DURATION * 1000)
		self.portal_cooldown_until = 0

	def try_accelerate_portal_cooldown(self, pos: Tuple[int, int]) -> bool:
		if self.portal_state != "cooldown" or len(self.portals) < 2:
			return False
		px, py = pos
		for portal in self.portals:
			cx, cy = portal.center
			if math.hypot(px - cx, py - cy) > PORTAL_INFUSION_RANGE:
				continue
			now = pygame.time.get_ticks()
			reduction_ms = int(PORTAL_COOLDOWN_REDUCTION * 1000)
			remaining = max(0, self.portal_cooldown_until - now)
			remaining = max(0, remaining - reduction_ms)
			if remaining == 0:
				self.activate_portals(now)
			else:
				self.portal_cooldown_until = now + remaining
			self.add_coin_popup(portal.center, f"-{int(PORTAL_COOLDOWN_REDUCTION)}s")
			return True
		return False

	def update_portals(self) -> None:
		if len(self.portals) < 2:
			self.portal_state = "inactive"
			self.portal_active_until = 0
			self.portal_cooldown_until = 0
			return
		now = pygame.time.get_ticks()
		if self.portal_state == "inactive":
			self.activate_portals(now)
			return
		if self.portal_state == "active":
			if now >= self.portal_active_until:
				self.portal_state = "cooldown"
				self.portal_cooldown_until = now + int(PORTAL_COOLDOWN_DURATION * 1000)
				self.portal_active_until = 0
			return
		if self.portal_state == "cooldown" and now >= self.portal_cooldown_until:
			self.activate_portals(now)

	def clone_pipes(self) -> List[PipeItem]:
		"""Make deep copies of all placed pipes so layouts can persist."""
		clones: List[PipeItem] = []
		for pipe in self.pipes:
			rect_copy = pipe.rect.copy() if pipe.rect else None
			clones.append(
				PipeItem(
					id=pipe.id,
					cost=pipe.cost,
					rect=rect_copy,
					entry_progress=pipe.entry_progress,
					exit_progress=pipe.exit_progress,
					entry_y=pipe.entry_y,
					exit_y=pipe.exit_y,
					x=pipe.x,
				)
			)
		return clones

	def clone_blocks(self) -> List[BlockItem]:
		"""Carry block placements forward with refreshed timers."""
		clones: List[BlockItem] = []
		now = pygame.time.get_ticks()
		for block in self.blocks:
			clone = BlockItem(
				id=block.id,
				cost=block.cost,
				progress=block.progress,
				pos=block.pos,
				radius=block.radius,
				active_duration=block.active_duration,
				cooldown_duration=block.cooldown_duration,
				upgrade_count=block.upgrade_count,
			)
			self.activate_block(clone, now)
			clones.append(clone)
		return clones

	def clone_turbo_pipes(self) -> List[TurboPipeItem]:
		"""Duplicate turbo pipes so layouts persist without shared references."""
		clones: List[TurboPipeItem] = []
		for turbo in self.turbo_pipes:
			clones.append(
				TurboPipeItem(
					id=turbo.id,
					cost=turbo.cost,
					start_progress=turbo.start_progress,
					end_progress=turbo.end_progress,
					length_progress=turbo.length_progress,
					positions=list(turbo.positions),
				)
			)
		return clones

	def clone_bouncers(self) -> List[BouncerItem]:
		"""Copy bounce pads so they persist across carried levels."""
		clones: List[BouncerItem] = []
		for bouncer in self.bouncers:
			clones.append(
				BouncerItem(
					id=bouncer.id,
					cost=bouncer.cost,
					center=bouncer.center,
					progress=bouncer.progress,
					radius=bouncer.radius,
					removals_remaining=bouncer.removals_remaining,
					ready_to_drop=bouncer.ready_to_drop,
				)
			)
		return clones

	def clone_storm_emitters(self) -> List[StormItem]:
		"""Preserve storm emitters when carrying layouts forward."""
		clones: List[StormItem] = []
		now = pygame.time.get_ticks()
		for storm in self.storm_emitters:
			clones.append(
				StormItem(
					id=storm.id,
					cost=storm.cost,
					center=storm.center,
					progress=storm.progress,
					radius=storm.radius,
					window_count=0,
					counted_eggs=0,
					animation_until=0,
					last_reward=0,
					settle_at=now + STORM_WINDOW_DURATION,
					expires_at=now + STORM_LIFETIME_MS,
				)
			)
		return clones

	def clone_portals(self) -> List[PortalItem]:
		"""Persist portal locations when carrying layouts forward."""
		clones: List[PortalItem] = []
		for portal in self.portals:
			clones.append(
				PortalItem(
					id=portal.id,
					cost=portal.cost,
					center=portal.center,
					progress=portal.progress,
					radius=portal.radius,
				)
			)
		return clones

	def get_pipe_by_id(self, pipe_id: Optional[int]) -> Optional[PipeItem]:
		if pipe_id is None:
			return None
		for pipe in self.pipes:
			if pipe.id == pipe_id:
				return pipe
		return None


def main() -> None:
	SpiralGame().run()


if __name__ == "__main__":
	main()
