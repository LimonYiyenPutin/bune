import os
import sys
import base64
import json

try:
    # --- GÜVENLİK VE DOSYA YOLLARI ---
    DATA_FOLDER = os.path.join(os.path.expanduser("~"), ".game_secure_data")
    SECRET_FILE = os.path.join(DATA_FOLDER, r"auth.key")
    SETUP_LOCK = os.path.join(DATA_FOLDER, r"installed.lock")
    SECRET_SIGNATURE = base64.b64encode(b"ANTI_CHEAT_SECURE_TOKEN_2026").decode('utf-8')

    def run_installer():
        if not os.path.exists(DATA_FOLDER):
            os.makedirs(DATA_FOLDER)
        with open(SECRET_FILE, "w", encoding="utf-8") as f:
            f.write(SECRET_SIGNATURE)
        with open(SETUP_LOCK, "w", encoding="utf-8") as f:
            f.write("LOCKED")

    if not os.path.exists(SETUP_LOCK):
        run_installer()

    def verify_security():
        if not os.path.exists(SECRET_FILE):
            return False
        try:
            with open(SECRET_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                return content == SECRET_SIGNATURE
        except Exception:
            return False

    if not verify_security():
        print("\n[!] HİLECİ! Güvenlik dosyaları silinmiş veya manipüle edilmiş. Oyun kapatılıyor.")
        input("Çıkmak için Enter'a basın...")
        sys.exit()

    PLAYERS_FILE = os.path.join(DATA_FOLDER, r'oyuncular.dat')

    def load_players():
        if not os.path.exists(PLAYERS_FILE):
            return {}
        try:
            with open(PLAYERS_FILE, 'r', encoding="utf-8") as f:
                encoded = f.read()
                decoded = base64.b64decode(encoded.encode('utf-8'))
                return json.loads(decoded.decode('utf-8'))
        except Exception:
            return {}

    def save_players(players_dict):
        try:
            json_str = json.dumps(players_dict)
            encoded = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
            with open(PLAYERS_FILE, 'w', encoding="utf-8") as f:
                f.write(encoded)
        except Exception:
            pass

    players_data = load_players()
    print("--- 3D SPEEDRUN OYUNU ---")
    username = input("Oyuncu adinizi girin: ").strip()
    if not username:
        username = "Misafir"

    if username in players_data:
        entered_pass = input(f"'{username}' adi kayitli. Sifrenizi girin: ")
        while entered_pass != players_data[username]['password']:
            print("Yanlis sifre!")
            entered_pass = input("Sifrenizi tekrar girin: ")
        print("Giris basarili!")
    else:
        new_pass = input(f"Yeni oyuncu '{username}' icin bir sifre belirleyin: ")
        players_data[username] = {'password': new_pass, 'best_time': None}
        save_players(players_data)
        print("Hesap olusturuldu ve kaydedildi!")

    from ursina import *
    import random

    app = Ursina()

    window.title = f'3D Speedrun - Oyuncu: {username}'
    window.borderless = False
    window.exit_button.visible = False
    window.fps_counter.enabled = True
    window.color = color.rgb(100, 180, 255)
    window.vsync = True

    random.seed()

    class GameManager:
        def __init__(self):
            self.target_score = 15
            self.current_user = username
            self.best_time = players_data[self.current_user].get('best_time', None)
            self.reset_values()

            self.score_text = Text(text='', position=(-0.85, 0.45), scale=1.1, color=color.gold)
            self.money_text = Text(text='', position=(-0.85, 0.40), scale=1.0, color=color.green)
            self.timer_text = Text(text='', position=(0.60, 0.45), scale=1.1, color=color.orange)
            self.best_text = Text(text='', position=(0.60, 0.40), scale=1.0, color=color.cyan)
            self.stamina_text = Text(text='Stamina: 100%', position=(-0.85, 0.35), scale=1.0, color=color.magenta)
            
            self.info_text = Text(
                text='WASD: Hareket | SHIFT: Kos | SPACE: Zipla | ESC: Menu',
                position=(-0.85, -0.45), scale=0.6, color=color.light_gray
            )

            self.overlay = Entity(parent=camera.ui, model='quad', scale=(2, 2), color=color.rgba(0, 0, 0, 220), z=1, enabled=False)
            self.title = Text(parent=camera.ui, text='', origin=(0, 0), position=(0.25, 0.25), scale=1.6, color=color.white, z=0, enabled=False)

            self.leaderboard_title = Text(parent=camera.ui, text='-- LİDERLİK TABLOSU --', position=(-0.75, 0.25), scale=1.1, color=color.gold, z=0, enabled=False)
            self.leaderboard_text = Text(parent=camera.ui, text='', position=(-0.75, 0.15), scale=0.9, color=color.white, z=0, enabled=False)

            self.resume_btn = Button(parent=camera.ui, text='Devam Et', position=(0.25, 0.05), scale=(0.25, 0.07), z=0, enabled=False, on_click=self.resume)
            self.restart_btn = Button(parent=camera.ui, text='Yeniden Basla', position=(0.25, -0.05), scale=(0.25, 0.07), z=0, enabled=False, on_click=self.restart)
            self.quit_btn = Button(parent=camera.ui, text='Cikis', position=(0.25, -0.15), scale=(0.25, 0.07), z=0, enabled=False, on_click=application.quit)

            self.message = None
            self.message_id = 0
            self.update_ui()

        def reset_values(self):
            self.score = 0
            self.money = 0
            self.elapsed_time = 0.0
            self.game_over = False
            self.win = False
            self.is_paused = False

        def update_ui(self):
            self.score_text.text = f'Altin: {self.score}/{self.target_score}'
            self.money_text.text = f'Para: {self.money} Akce'
            self.timer_text.text = f'Sure: {round(self.elapsed_time, 1)}s'
            if self.best_time:
                self.best_text.text = f'En Iyi: {round(self.best_time, 1)}s'
            else:
                self.best_text.text = 'En Iyi: Yok'
            
            if 'player' in globals():
                self.stamina_text.text = f'Stamina: {int(player.stamina)}%'

        def show_message(self, message, col=color.white):
            self.message_id += 1
            current_id = self.message_id
            if self.message:
                destroy(self.message)
            self.message = Text(parent=camera.ui, text=message, origin=(0, 0), position=(0, 0.32), scale=1.2, color=col, z=0)
            invoke(self.clear_message, current_id, delay=2)

        def clear_message(self, message_id):
            if message_id != self.message_id:
                return
            if self.message:
                destroy(self.message)
                self.message = None

        def update_leaderboard_display(self):
            sorted_players = sorted(
                [(name, data.get('best_time')) for name, data in players_data.items() if data.get('best_time') is not None],
                key=lambda x: x[1]
            )
            lb_str = ""
            for idx, (p_name, p_time) in enumerate(sorted_players[:8], 1):
                lb_str += f"{idx}. {p_name} -> {round(p_time, 1)}s\n"
            if not lb_str:
                lb_str = "Henuz rekor kaydedilmedi."
            self.leaderboard_text.text = lb_str

        def show_menu(self, title, col=color.white, show_resume=False):
            self.overlay.enable()
            self.title.text = title
            self.title.color = col
            self.title.enable()
            
            self.update_leaderboard_display()
            self.leaderboard_title.enable()
            self.leaderboard_text.enable()

            self.resume_btn.enabled = show_resume
            self.restart_btn.enable()
            self.quit_btn.enable()
            mouse.locked = False
            mouse.visible = True

        def hide_menu(self):
            self.overlay.disable()
            self.title.disable()
            self.leaderboard_title.disable()
            self.leaderboard_text.disable()
            self.resume_btn.disable()
            self.restart_btn.disable()
            self.quit_btn.disable()

        def resume(self):
            if self.game_over or self.win:
                return
            self.is_paused = False
            self.hide_menu()
            mouse.locked = True
            mouse.visible = False

        def finish(self, won, reason=''):
            if self.game_over or self.win:
                return

            self.win = won
            self.game_over = not won

            if won:
                final_score_time = round(self.elapsed_time, 1)
                if self.best_time is None or final_score_time < self.best_time:
                    self.best_time = final_score_time
                    players_data[self.current_user]['best_time'] = self.best_time
                    save_players(players_data)
                    text = f'YENİ REKOR! 🎉\nSure: {final_score_time}s\nKazanc: {self.money} Akce'
                else:
                    text = f'TEBRIKLER, KAZANDIN!\nSure: {final_score_time}s\nKazanc: {self.money} Akce'
                col = color.green
            else:
                text = f'OYUN BITTI!\n{reason}'
                col = color.red

            self.show_menu(text, col, show_resume=False)
            player.enabled = False

        def restart(self):
            self.reset_values()
            self.hide_menu()
            if self.message:
                destroy(self.message)
                self.message = None
            self.message_id += 1

            player.enabled = True
            player.position = Vec3(0, 3, 0)
            player.rotation = Vec3(0, 0, 0)
            player.vy = 0
            player.is_grounded = False
            player.stamina = 100.0

            for obj in coins + diamonds:
                obj.position = Vec3(*obj.start_position)
                obj.rotation = Vec3(*obj.start_rotation)
                obj.enable()

            self.update_ui()
            mouse.locked = True
            mouse.visible = False

    game = GameManager()

    ground = Entity(
        model='plane',
        scale=(80, 1, 80),
        color=color.rgb(40, 160, 60),
        texture='white_cube',
        texture_scale=(40, 40),
        collider='box'
    )

    sky = Sky(color=color.rgb(100, 180, 255))

    class Player(Entity):
        def __init__(self):
            super().__init__(
                model='cube',
                color=color.orange,
                scale=(1, 2, 1),
                position=(0, 3, 0),
                collider='box'
            )

            self.normal_speed = 6
            self.run_speed = 11
            self.speed = self.normal_speed
            
            self.gravity = 20
            self.jump_force = 12
            self.vy = 0
            self.is_grounded = False

            self.stamina = 100.0
            self.max_stamina = 100.0
            self.stamina_drain_rate = 25.0
            self.stamina_regen_rate = 10.0

            self.camera_pivot = Entity(parent=self, position=(0, 0.7, 0))
            camera.parent = self.camera_pivot
            camera.position = (0, 1.1, -8)
            camera.rotation = (5, 0, 0)
            camera.fov = 90

        def update(self):
            if game.is_paused or game.game_over or game.win:
                return

            dt = time.dt

            self.rotation_y += mouse.velocity[0] * 100
            self.camera_pivot.rotation_x -= mouse.velocity[1] * 100
            self.camera_pivot.rotation_x = clamp(self.camera_pivot.rotation_x, -35, 55)

            move_x = held_keys['d'] - held_keys['a']
            move_z = held_keys['w'] - held_keys['s']
            move_dir = Vec3(move_x, 0, move_z)

            is_moving = move_dir.length() > 0
            is_running = held_keys['shift'] and is_moving and self.stamina > 0

            if is_running:
                self.speed = self.run_speed
                self.stamina = max(0.0, self.stamina - self.stamina_drain_rate * dt)
            else:
                self.speed = self.normal_speed
                if self.stamina < self.max_stamina and not held_keys['shift']:
                    self.stamina = min(self.max_stamina, self.stamina + self.stamina_regen_rate * dt)

            if is_moving:
                move_dir = move_dir.normalized()
                move_vector = (self.right * move_dir.x + self.forward * move_dir.z)
                move_vector.y = 0
                self.position += move_vector * self.speed * dt

            was_falling = self.vy <= 0
            self.vy -= self.gravity * dt
            self.y += self.vy * dt

            if was_falling:
                hit = raycast(
                    self.world_position + Vec3(0, 0.05, 0),
                    Vec3(0, -1, 0),
                    distance=1.15,
                    ignore=[self],
                    debug=False
                )
                if hit.hit and self.y >= hit.world_point.y:
                    self.y = hit.world_point.y + 1
                    self.vy = 0
                    self.is_grounded = True
                else:
                    self.is_grounded = False
            else:
                self.is_grounded = False

            if self.y < -10:
                game.finish(False, "Boşluğa düştün!")
                return

    player = Player()
    mouse.locked = True
    mouse.visible = False

    coins = []
    diamonds = []

    for i in range(game.target_score):
        pos = Vec3(random.randint(-35, 35), 0.5, random.randint(-35, 35))
        coin = Entity(model='sphere', color=color.gold, scale=0.7, position=pos, collider='sphere')
        coin.start_position = tuple(pos)
        coin.start_rotation = tuple(coin.rotation)
        coins.append(coin)

    for i in range(2):
        pos = Vec3(random.randint(-35, 35), 0.5, random.randint(-35, 35))
        diamond = Entity(model='diamond', color=color.cyan, scale=0.85, position=pos, collider='box')
        diamond.start_position = tuple(pos)
        diamond.start_rotation = tuple(diamond.rotation)
        diamonds.append(diamond)

    def update():
        if game.is_paused or game.game_over or game.win:
            return

        dt = time.dt
        game.elapsed_time += dt
        game.update_ui()

        for coin in coins:
            if coin.enabled:
                coin.rotation_y += 100 * dt

        for diamond in diamonds:
            if diamond.enabled:
                diamond.rotation_y += 80 * dt
                diamond.rotation_z += 40 * dt

        for coin in coins:
            if coin.enabled and distance(player.position, coin.position) < 1.4:
                coin.disable()
                game.score += 1
                game.money += 15
                game.update_ui()

                if game.score >= game.target_score:
                    game.finish(True)
                    return

        for diamond in diamonds:
            if diamond.enabled and distance(player.position, diamond.position) < 1.4:
                diamond.disable()
                player.stamina = 100.0
                game.money += 75
                game.update_ui()
                game.show_message('Elmas bulundu! Stamina Full!', color.cyan)

    def input(key):
        if key == 'escape':
            if game.game_over or game.win:
                return
            if game.is_paused:
                game.resume()
            else:
                game.is_paused = True
                game.show_menu('OYUN DURAKLATILDI', color.white, show_resume=True)

        # DÜZELTME: Bu kısım doğruca input(key) fonksiyonunun içine alındı
        if key == 'space':
            if not game.is_paused and not game.game_over and not game.win and player.is_grounded:
                player.vy = player.jump_force
                player.is_grounded = False

    app.run()

except Exception as e:
    import traceback
    print("\n[!] Oyun çalışırken bir hata oluştu:")
    traceback.print_exc()
    input("\nKapatmak için Enter tuşuna basın...")