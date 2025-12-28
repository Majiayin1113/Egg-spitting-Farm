"""Gradio wrapper to run the SpiralGame demo inside a Hugging Face Space."""

from __future__ import annotations

import os
import threading
from typing import Optional, Tuple

# Ensure pygame can initialize without a physical display/audio device.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import gradio as gr
import numpy as np
import pygame

import gametest

HEADLESS_FPS = 30


class GameSession:
    """Continuously runs the pygame simulation and exposes helper controls."""

    def __init__(self) -> None:
        pygame.init()
        self.game = gametest.SpiralGame()
        self.lock = threading.Lock()
        self.paused = False
        self.running = True
        self.last_frame: Optional[np.ndarray] = None
        self.last_status: str = "Booting..."
        self.mouse_pos: Tuple[int, int] = (0, 0)
        self._loop_thread = threading.Thread(target=self._loop, daemon=True)
        self._loop_thread.start()

    def _loop(self) -> None:
        while self.running:
            dt = self.game.clock.tick(HEADLESS_FPS) / 1000.0
            pygame.event.pump()
            with self.lock:
                if not self.paused:
                    self.game.update(dt)
                self.last_frame, self.last_status = self._render_locked()

    def _render_locked(self) -> Tuple[np.ndarray, str]:
        remaining = self.game.remaining_time()
        self.game.screen.fill(gametest.BG_COLOR)
        self.game.draw_shop()
        self.game.draw_power_bar()
        self.game.draw_track()
        self.game.draw_machine()
        self.game.draw_balls()
        self.game.draw_coin_popups()
        self.game.draw_panel(remaining)
        self.game.draw_footer(remaining)
        self.game.draw_skill_overlay()
        self.game.draw_shop_tooltip()
        pygame.display.flip()
        frame = pygame.surfarray.array3d(self.game.screen)
        frame = np.transpose(frame, (1, 0, 2))
        status = self._status_text(remaining)
        return frame, status

    def _status_text(self, remaining: int) -> str:
        target = self.game.level_target()
        goal = f"Score {self.game.score}/{target}"
        coins = f"Coins {self.game.coins}"
        timers = "Complete" if not self.game.round_active else f"{remaining:02d}s left"
        result = self.game.round_result or "playing"
        state = "Paused" if self.paused else "Running"
        return (
            f"Level {self.game.current_level}/{self.game.max_level} • {goal}"
            f" • {coins} • {len(self.game.balls)} balls • {timers} • {state} ({result})"
        )

    def get_frame(self) -> Tuple[np.ndarray, str]:
        with self.lock:
            if self.last_frame is None:
                self.last_frame, self.last_status = self._render_locked()
            return self.last_frame.copy(), self.last_status

    def toggle_pause(self) -> bool:
        with self.lock:
            self.paused = not self.paused
            self.last_frame, self.last_status = self._render_locked()
            return self.paused

    def click(self, coords: Tuple[int, int], button: str = "left") -> None:
        pos = (int(coords[0]), int(coords[1]))
        pygame.mouse.set_pos(pos)
        with self.lock:
            if button == "left":
                self.game.handle_click(pos)
            else:
                self.game.handle_right_click(pos)
            self.last_frame, self.last_status = self._render_locked()

    def command(self, action: str) -> None:
        with self.lock:
            if action == "retry":
                self.game.reset_round(self.game.current_level)
            elif action == "next" and self.game.round_result == "success":
                next_level = (
                    self.game.current_level + 1
                    if self.game.current_level < self.game.max_level
                    else 1
                )
                carry_layout = next_level > self.game.current_level
                self.game.reset_round(next_level, carry_items=carry_layout)
            elif action == "reset":
                self.game.reset_round(1)
            self.last_frame, self.last_status = self._render_locked()


session = GameSession()


def startup() -> Tuple[np.ndarray, str]:
    return session.get_frame()


def refresh_view() -> Tuple[np.ndarray, str]:
    return session.get_frame()


def handle_canvas_click(mode: str, evt: gr.SelectData | None) -> Tuple[np.ndarray, str]:
    if not evt:
        return session.get_frame()
    coords = evt.index if isinstance(evt.index, (tuple, list)) else evt.value
    if not coords:
        return session.get_frame()
    x, y = coords[0], coords[1]
    button = "right" if mode == "Remove / Right Click" else "left"
    session.click((x, y), button=button)
    return session.get_frame()


def handle_retry() -> Tuple[np.ndarray, str]:
    session.command("retry")
    return session.get_frame()


def handle_next_level() -> Tuple[np.ndarray, str]:
    session.command("next")
    return session.get_frame()


def handle_full_reset() -> Tuple[np.ndarray, str]:
    session.command("reset")
    return session.get_frame()


def handle_pause_toggle() -> Tuple[np.ndarray, str, gr.Button]:
    paused = session.toggle_pause()
    frame, status = session.get_frame()
    label = "Resume Simulation" if paused else "Pause Simulation"
    return frame, status, gr.Button.update(value=label)


with gr.Blocks(title="Egg-spitting-Farm (Gradio)") as demo:
    gr.Markdown(
        """
        ### Egg-spitting-Farm · Hugging Face build
        - 左键在画面中直接下单或操作道具
        - 切换到 **Remove / Right Click** 模式来回收放置物
        - 使用下方按钮快速重开、下一关或整体重置
        - 画面每 0.2s 自动刷新，可随时点击 `Pause` 来节省资源
        """
    )

    with gr.Row():
        game_image = gr.Image(
            label="Live View",
            type="numpy",
            height=gametest.HEIGHT,
            width=gametest.WIDTH,
        )
        with gr.Column():
            status_md = gr.Markdown("Loading...")
            click_mode = gr.Radio(
                ["Interact / Left Click", "Remove / Right Click"],
                label="Click Mode",
                value="Interact / Left Click",
            )
            pause_button = gr.Button("Pause Simulation", variant="secondary")
            retry_button = gr.Button("Retry Level (Space)")
            next_button = gr.Button("Next Level (Enter)")
            reset_button = gr.Button("Reset To Level 1 (R)")

    demo.load(fn=startup, inputs=None, outputs=[game_image, status_md])
    demo.load(fn=refresh_view, inputs=None, outputs=[game_image, status_md], every=0.2)

    game_image.select(
        fn=handle_canvas_click,
        inputs=[click_mode],
        outputs=[game_image, status_md],
    )
    pause_button.click(
        fn=handle_pause_toggle,
        inputs=None,
        outputs=[game_image, status_md, pause_button],
    )
    retry_button.click(fn=handle_retry, inputs=None, outputs=[game_image, status_md])
    next_button.click(fn=handle_next_level, inputs=None, outputs=[game_image, status_md])
    reset_button.click(fn=handle_full_reset, inputs=None, outputs=[game_image, status_md])


def main() -> None:
    demo.queue().launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
        show_api=False,
    )


if __name__ == "__main__":
    main()
