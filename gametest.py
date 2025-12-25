"""Z-path ball drop mini-game for quick playtesting."""

from __future__ import annotations

import math
from bisect import bisect_left
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import pygame


WIDTH, HEIGHT = 900, 700
SHOP_WIDTH = 160
UTILITY_WIDTH = 160
FONT_LARGE_SIZE = 30
FONT_SMALL_SIZE = 18
BG_COLOR = (12, 16, 25)
TRACK_COLOR = (51, 178, 255)
MACHINE_COLOR = (255, 180, 64)
PANEL_COLOR = (24, 34, 52)
PANEL_BORDER = (90, 110, 160)
BALL_COLORS = [(255, 92, 138), (255, 214, 102), (130, 255, 173), (138, 189, 255)]

SPAWN_INTERVAL = 0.3
ROUND_TIME = 60
LEVEL_CONFIG = {
	1: {"target": 180, "blocks": False},
	2: {"target": 300, "blocks": True},
	3: {"target": 800, "blocks": True},
}
PIPE_COST_SCHEDULE = [10, 20, 25, 40, 60]
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
BLOCK_COST_SCHEDULE = [16, 25, 30, 38, 40, 50]
SPEED_BOOST_DURATION = 3.0
SPEED_BOOST_FACTOR = 2.0
SPECIAL_EGG_VALUE = 10
SPECIAL_EGG_COLORS = ((255, 250, 160), (255, 110, 150))
COIN_RAIN_RATE = 8
SKILL_BUTTON_HEIGHT = 56
SKILL_PANEL_MARGIN = 16
SKILL_INFO = {
	"super_egg": {"title": "Lucky Egg", "desc": "Every 5th = 10 pts"},
	"coin_rain": {"title": "Coin Rain", "desc": "+8 coins/sec"},
}


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
	bonus_score: int = 0
	score_value: int = 1
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

		self.machine_pos = (WIDTH // 2, 70)
		self.shop_rect = pygame.Rect(0, 0, SHOP_WIDTH, HEIGHT)
		self.pipe_button = pygame.Rect(20, 180, SHOP_WIDTH - 40, 140)
		self.block_button = pygame.Rect(20, 360, SHOP_WIDTH - 40, 140)
		self.utility_rect = pygame.Rect(WIDTH - UTILITY_WIDTH, 0, UTILITY_WIDTH, HEIGHT)
		self.speed_boost_button = pygame.Rect(
			self.utility_rect.x + 20,
			200,
			self.utility_rect.width - 40,
			140,
		)
		skill_panel_height = 230
		self.skill_panel_rect = pygame.Rect(
			self.utility_rect.x + 10,
			self.utility_rect.bottom - skill_panel_height - 20,
			self.utility_rect.width - 20,
			skill_panel_height,
		)
		btn_width = self.skill_panel_rect.width - 2 * SKILL_PANEL_MARGIN
		btn_x = self.skill_panel_rect.x + SKILL_PANEL_MARGIN
		btn_y = self.skill_panel_rect.y + 80
		self.skill_buttons = {
			"super_egg": pygame.Rect(btn_x, btn_y, btn_width, SKILL_BUTTON_HEIGHT),
			"coin_rain": pygame.Rect(
				btn_x,
				btn_y + SKILL_BUTTON_HEIGHT + 10,
				btn_width,
				SKILL_BUTTON_HEIGHT,
			),
		}
		self.pipe_counter = 0
		self.block_counter = 0
		self.pipes: List[PipeItem] = []
		self.blocks: List[BlockItem] = []
		self.placing_pipe: Optional[PipeItem] = None
		self.placing_block: Optional[BlockItem] = None
		self.speed_boost_active_until = 0
		self.speed_boost_unlocked = False
		self.skill_choice: Optional[str] = None
		self.skill_selection_required = False
		self.skill_coin_timer = 0.0
		self.spawned_ball_count = 0
		self.level_configs = LEVEL_CONFIG
		self.max_level = max(self.level_configs.keys()) if self.level_configs else 1
		self.current_level = max(1, min(start_level, self.max_level))
		self.reset_round()

	def reset_round(self, level: Optional[int] = None) -> None:
		if level is not None:
			self.current_level = max(1, min(level, self.max_level))
		self.balls: List[Ball] = []
		self.score = 0
		self.coins = 0
		self.spawn_timer = 0.0
		self.round_start_ms: Optional[int] = None
		self.round_active = True
		self.round_result: Optional[str] = None
		self.pipes = []
		self.placing_pipe = None
		self.pipe_counter = 0
		self.pipe_purchases = 0
		self.blocks = []
		self.block_counter = 0
		self.block_purchases = 0
		self.placing_block = None
		self.speed_boost_unlocked = self.current_level >= 3
		self.speed_boost_active_until = 0
		self.skill_choice = None
		self.skill_selection_required = self.current_level >= 3
		self.skill_coin_timer = 0.0
		self.spawned_ball_count = 0
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

	def level_target(self) -> int:
		cfg = self.level_configs.get(self.current_level, {})
		return cfg.get("target", 0)

	def blocks_enabled(self) -> bool:
		cfg = self.level_configs.get(self.current_level, {})
		return cfg.get("blocks", False)

	def speed_boost_active(self) -> bool:
		if not self.speed_boost_unlocked:
			return False
		return pygame.time.get_ticks() < self.speed_boost_active_until

	def speed_boost_multiplier(self) -> float:
		return SPEED_BOOST_FACTOR if self.speed_boost_active() else 1.0

	def can_use_speed_boost(self) -> bool:
		return (
			self.speed_boost_unlocked
			and not self.speed_boost_active()
			and self.round_active
			and self.round_start_ms is not None
		)

	def try_activate_speed_boost(self) -> None:
		if not self.can_use_speed_boost():
			return
		self.speed_boost_active_until = pygame.time.get_ticks() + int(SPEED_BOOST_DURATION * 1000)

	def skill_status_text(self) -> str:
		if self.current_level < 3:
			return "Passive: Locked"
		if self.skill_choice:
			info = SKILL_INFO.get(self.skill_choice, {})
			return f"Passive: {info.get('title', 'Equipped')}"
		if self.skill_selection_required:
			return "Passive: Choose a perk"
		return "Passive: None"

	def handle_skill_selection_click(self, pos: Tuple[int, int]) -> bool:
		if self.current_level < 3 or not self.skill_selection_required:
			return False
		for key, rect in self.skill_buttons.items():
			if rect.collidepoint(pos):
				self.select_skill(key)
				return True
		return False

	def select_skill(self, key: str) -> None:
		if key not in SKILL_INFO:
			return
		self.skill_choice = key
		self.skill_selection_required = False
		self.start_round_clock()

	def spawn_ball(self) -> None:
		self.spawned_ball_count += 1
		special = self.skill_choice == "super_egg" and self.spawned_ball_count % 5 == 0
		value = SPECIAL_EGG_VALUE if special else 1
		color_index = len(self.balls) % len(BALL_COLORS)
		self.balls.append(
			Ball(
				color_index=color_index,
				score_value=value,
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
				self.apply_block_effects(ball)
			if self.apply_pipe(ball, dt):
				continue
			if ball.distance >= self.track_total:
				completed.append(ball)
		if completed:
			if self.round_active:
				for fin in completed:
					gain = fin.score_value + fin.bonus_score
					self.score += gain
					self.coins += gain
			self.balls = [b for b in self.balls if b not in completed]

	def remaining_time(self) -> int:
		if self.round_start_ms is None:
			return ROUND_TIME
		elapsed = (pygame.time.get_ticks() - self.round_start_ms) / 1000.0
		remaining = max(0, ROUND_TIME - int(elapsed))
		if remaining == 0 and self.round_active:
			self.round_active = False
			target = self.level_target()
			self.round_result = "success" if self.score >= target else "fail"
		return remaining

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
		self.apply_skill_income(dt)

	def draw_track(self) -> None:
		pygame.draw.lines(self.screen, TRACK_COLOR, False, self.track_points, 4)
		for pipe in self.pipes:
			if pipe.rect:
				pygame.draw.rect(self.screen, (255, 255, 255), pipe.rect, border_radius=6)
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
		rect = pygame.Rect(SHOP_WIDTH + 20, 20, 260, 180)
		pygame.draw.rect(self.screen, PANEL_COLOR, rect, border_radius=12)
		pygame.draw.rect(self.screen, PANEL_BORDER, rect, width=2, border_radius=12)

		score_text = self.font_large.render(f"Score: {self.score}", True, (255, 255, 255))
		self.screen.blit(score_text, (rect.x + 16, rect.y + 10))

		coin_text = self.font_small.render(f"Coins: {self.coins}", True, (255, 220, 140))
		self.screen.blit(coin_text, (rect.x + 16, rect.y + 66))
		
		pipe_text = self.font_small.render(
			f"Pipes: {len(self.pipes)}", True, (180, 220, 255)
		)
		self.screen.blit(pipe_text, (rect.x + 140, rect.y + 10))

		if self.blocks_enabled():
			block_text = self.font_small.render(
				f"Blocks: {len(self.blocks)}", True, (200, 180, 255)
			)
			self.screen.blit(block_text, (rect.x + 140, rect.y + 38))

		timer_text = self.font_small.render(f"Time: {remaining:02d}s", True, (180, 220, 255))
		self.screen.blit(timer_text, (rect.x + 140, rect.y + 66))

		level_text = self.font_small.render(
			f"Level {self.current_level}", True, (180, 220, 255)
		)
		self.screen.blit(level_text, (rect.x + 16, rect.y + 94))

		target = self.level_target()
		goal_text = self.font_small.render(f"Goal: {target}", True, (255, 200, 160))
		self.screen.blit(goal_text, (rect.x + 16, rect.y + 122))

		status_y = rect.y + 148
		if self.current_level >= 3:
			skill_text = self.font_small.render(self.skill_status_text(), True, (160, 255, 200))
			self.screen.blit(skill_text, (rect.x + 16, status_y))
			status_y += 28
		if not self.round_active:
			if self.round_result == "fail":
				fail_text = self.font_small.render(
					"Press Space to retry", True, (255, 120, 120)
				)
				self.screen.blit(fail_text, (rect.x + 16, status_y))
			else:
				if self.current_level < self.max_level:
					next_label = self.current_level + 1
					msg = f"Press Enter for Lv {next_label}"
				else:
					msg = "Press Enter to restart"
				win_text = self.font_small.render(msg, True, (120, 255, 200))
				self.screen.blit(win_text, (rect.x + 16, status_y))

	def draw_footer(self, remaining: int) -> None:
		if self.round_start_ms is None and self.current_level >= 3:
			message = "Select a passive skill to start"
		elif not self.round_active:
			if self.round_result == "fail":
				message = "Goal missed. Press Space to retry"
			else:
				if self.current_level < self.max_level:
					next_label = self.current_level + 1
					message = f"Success! Press Enter for Level {next_label}"
				else:
					message = "All clear! Press Enter to restart"
		else:
			message = "Catch every drop!"
		text = self.font_small.render(message, True, (200, 200, 210))
		x_pos = WIDTH - UTILITY_WIDTH - text.get_width() - 20
		x_pos = max(SHOP_WIDTH + 20, x_pos)
		self.screen.blit(text, (x_pos, HEIGHT - 40))

	def draw_shop(self) -> None:
		pygame.draw.rect(self.screen, (18, 26, 41), self.shop_rect)
		pygame.draw.line(self.screen, PANEL_BORDER, (SHOP_WIDTH, 0), (SHOP_WIDTH, HEIGHT), 2)
		title = self.font_small.render("Shop", True, (255, 255, 255))
		self.screen.blit(title, (20, 20))

		info = self.font_small.render("Buy gadgets", True, (150, 180, 210))
		self.screen.blit(info, (20, 50))

		current_cost = self.next_pipe_cost()
		btn_color = (70, 120, 200)
		if self.placing_pipe:
			btn_color = (200, 180, 80)
		elif self.coins < current_cost:
			btn_color = (45, 60, 90)
		pygame.draw.rect(self.screen, btn_color, self.pipe_button, border_radius=10)
		pygame.draw.rect(self.screen, (255, 255, 255), self.pipe_button, 2, border_radius=10)
		label = "Vertical Pipe"
		label_text = self.font_small.render(label, True, (12, 16, 25))
		self.screen.blit(
			label_text,
			(
				self.pipe_button.centerx - label_text.get_width() // 2,
				self.pipe_button.y + 16,
			),
		)
		cost_text = self.font_small.render(f"Cost: {current_cost}", True, (12, 16, 25))
		self.screen.blit(
			cost_text,
			(
				self.pipe_button.centerx - cost_text.get_width() // 2,
				self.pipe_button.y + 46,
			),
		)
		state_msg = "Placing..." if self.placing_pipe else "Click to place"
		state_text = self.font_small.render(state_msg, True, (12, 16, 25))
		self.screen.blit(
			state_text,
			(
				self.pipe_button.centerx - state_text.get_width() // 2,
				self.pipe_button.y + 76,
			),
		)

		owned_text = self.font_small.render(
			f"Owned: {len(self.pipes)}", True, (150, 200, 255)
		)
		self.screen.blit(owned_text, (20, self.pipe_button.bottom + 12))

		if self.blocks_enabled():
			self.draw_block_button()

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
		tip = self.font_small.render("Quick boosts", True, (150, 180, 210))
		self.screen.blit(tip, (self.utility_rect.x + 20, 50))

		btn_color = (70, 160, 140)
		state_msg = "Click to surge"
		locked = not self.speed_boost_unlocked
		if locked:
			btn_color = (45, 60, 90)
			state_msg = "Unlock Lv3"
		elif self.speed_boost_active():
			btn_color = (220, 200, 90)
			state_msg = "Active"

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
					self.speed_boost_button.y + 106,
				),
			)

		self.draw_skill_panel()

	def draw_skill_panel(self) -> None:
		panel = self.skill_panel_rect
		pygame.draw.rect(self.screen, PANEL_COLOR, panel, border_radius=12)
		pygame.draw.rect(self.screen, PANEL_BORDER, panel, 2, border_radius=12)
		title = self.font_small.render("Passive Skills", True, (255, 255, 255))
		self.screen.blit(title, (panel.x + 12, panel.y + 10))
		desc = self.font_small.render("Select before Lv3", True, (150, 180, 210))
		self.screen.blit(desc, (panel.x + 12, panel.y + 34))
		if self.current_level < 3:
			locked = self.font_small.render("Unlocks at Level 3", True, (255, 180, 120))
			self.screen.blit(locked, (panel.x + 12, panel.y + 70))
			return
		awaiting_choice = self.skill_selection_required and self.skill_choice is None
		for key in ("super_egg", "coin_rain"):
			rect = self.skill_buttons[key]
			info = SKILL_INFO.get(key, {})
			selected = self.skill_choice == key
			if selected:
				btn_color = (90, 200, 150)
				state = "Active"
			elif awaiting_choice:
				btn_color = (70, 120, 200)
				state = "Click to equip"
			else:
				btn_color = (45, 60, 90)
				state = "Inactive"
			pygame.draw.rect(self.screen, btn_color, rect, border_radius=10)
			pygame.draw.rect(self.screen, (255, 255, 255), rect, 2, border_radius=10)
			label = self.font_small.render(info.get("title", key.title()), True, (12, 16, 25))
			self.screen.blit(
				label,
				(rect.centerx - label.get_width() // 2, rect.y + 6),
			)
			detail = self.font_small.render(info.get("desc", "Passive bonus"), True, (12, 16, 25))
			self.screen.blit(
				detail,
				(rect.centerx - detail.get_width() // 2, rect.y + 30),
			)
			state_text = self.font_small.render(state, True, (12, 16, 25))
			self.screen.blit(
				state_text,
				(rect.centerx - state_text.get_width() // 2, rect.y + SKILL_BUTTON_HEIGHT - 16),
			)

	def draw_block_button(self) -> None:
		current_cost = self.next_block_cost()
		btn_color = (120, 80, 160)
		if self.placing_block:
			btn_color = (230, 200, 100)
		elif self.coins < current_cost:
			btn_color = (55, 38, 70)
		pygame.draw.rect(self.screen, btn_color, self.block_button, border_radius=10)
		pygame.draw.rect(self.screen, (255, 255, 255), self.block_button, 2, border_radius=10)
		label_text = self.font_small.render("Slow Block", True, (12, 16, 25))
		self.screen.blit(
			label_text,
			(
				self.block_button.centerx - label_text.get_width() // 2,
				self.block_button.y + 16,
			),
		)
		cost_text = self.font_small.render(f"Cost: {current_cost}", True, (12, 16, 25))
		self.screen.blit(
			cost_text,
			(
				self.block_button.centerx - cost_text.get_width() // 2,
				self.block_button.y + 46,
			),
		)
		state_msg = "Placing..." if self.placing_block else "Slow +5"
		state_text = self.font_small.render(state_msg, True, (12, 16, 25))
		self.screen.blit(
			state_text,
			(
				self.block_button.centerx - state_text.get_width() // 2,
				self.block_button.y + 76,
			),
		)
		owned_text = self.font_small.render(
			f"Blocks: {len(self.blocks)}", True, (200, 180, 255)
		)
		self.screen.blit(owned_text, (20, self.block_button.bottom + 20))

	def draw_blocks(self) -> None:
		now = pygame.time.get_ticks()
		for block in self.blocks:
			x, y = block.pos
			rect = pygame.Rect(0, 0, block.radius * 2, block.radius * 2)
			rect.center = (int(x), int(y))
			pygame.draw.rect(self.screen, (255, 140, 90), rect, border_radius=6)
			pygame.draw.rect(self.screen, (255, 255, 255), rect, 2, border_radius=6)
			remaining = max(0.0, BLOCK_DURATION - (now - block.spawn_ms) / 1000.0)
			seconds = max(0, int(math.ceil(remaining)))
			text = self.font_small.render(str(seconds), True, (12, 16, 25))
			text_rect = text.get_rect(center=rect.center)
			self.screen.blit(text, text_rect)

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
					if not self.round_active:
						if event.key == pygame.K_SPACE and self.round_result == "fail":
							self.reset_round(self.current_level)
						elif event.key == pygame.K_RETURN and self.round_result == "success":
							next_level = self.current_level + 1 if self.current_level < self.max_level else 1
							self.reset_round(next_level)
						elif event.key == pygame.K_r:
							self.reset_round(1)
				elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
					self.handle_click(event.pos)

			remaining = self.remaining_time()
			self.update(dt)

			self.screen.fill(BG_COLOR)
			self.draw_shop()
			self.draw_power_bar()
			self.draw_track()
			self.draw_machine()
			self.draw_balls()
			self.draw_panel(remaining)
			self.draw_footer(remaining)

			pygame.display.flip()

		pygame.quit()

	def handle_click(self, pos: Tuple[int, int]) -> None:
		if self.handle_skill_selection_click(pos):
			return
		if self.pipe_button.collidepoint(pos):
			self.try_purchase_pipe()
			return
		if self.blocks_enabled() and self.block_button.collidepoint(pos):
			self.try_purchase_block()
			return
		if self.speed_boost_button.collidepoint(pos):
			self.try_activate_speed_boost()
			return
		play_min = SHOP_WIDTH + 20
		play_max = WIDTH - UTILITY_WIDTH - 20
		if self.placing_pipe and play_min < pos[0] < play_max:
			self.place_pipe(pos)
		elif self.placing_block and play_min < pos[0] < play_max:
			self.place_block(pos)

	def try_purchase_pipe(self) -> None:
		if self.placing_pipe or self.placing_block:
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
		if self.placing_block or self.placing_pipe:
			return
		cost = self.next_block_cost()
		if self.coins < cost:
			return
		self.coins -= cost
		self.block_counter += 1
		self.block_purchases += 1
		self.placing_block = BlockItem(id=self.block_counter, cost=cost)

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
		pipe = self.placing_pipe
		pipe.rect = rect
		pipe.entry_progress = entry_prog
		pipe.exit_progress = exit_prog
		pipe.entry_y = entry_y
		pipe.exit_y = exit_y
		pipe.x = rect.centerx
		self.pipes.append(pipe)
		self.pipes.sort(key=lambda item: item.entry_progress)
		self.placing_pipe = None

	def place_block(self, pos: Tuple[int, int]) -> None:
		if not self.placing_block:
			return
		x, y, progress = self.nearest_point_on_track(pos)
		block = self.placing_block
		block.pos = (x, y)
		block.progress = progress
		block.spawn_ms = pygame.time.get_ticks()
		self.blocks.append(block)
		self.placing_block = None

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

	def update_blocks(self) -> None:
		if not self.blocks:
			return
		now = pygame.time.get_ticks()
		self.blocks = [
			block for block in self.blocks if (now - block.spawn_ms) / 1000.0 < BLOCK_DURATION
		]

	def apply_skill_income(self, dt: float) -> None:
		if self.skill_choice != "coin_rain" or not self.round_active:
			return
		self.skill_coin_timer += dt
		while self.skill_coin_timer >= 1.0:
			self.coins += COIN_RAIN_RATE
			self.skill_coin_timer -= 1.0

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
			if block.id in ball.block_hits:
				continue
			block_distance = self.progress_to_distance(block.progress)
			if ball.last_distance < block_distance <= ball.distance:
				ball.speed = max(ball.speed * BLOCK_SLOW_FACTOR, 0.0)
				ball.block_hits.add(block.id)
				ball.bonus_score += BLOCK_BONUS

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
