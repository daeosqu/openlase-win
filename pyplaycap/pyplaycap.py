import os
import sys
import time
import math
import json
import colorsys

import cv2
from cv2_enumerate_cameras import enumerate_cameras
import tkinter as tk
from tkinter import Label, Button, Scale, HORIZONTAL, Frame, Radiobutton, StringVar, filedialog, messagebox, Checkbutton
from PIL import Image, ImageTk
import numpy as np

if os.name == 'nt':
    os.add_dll_directory(r"C:\Windows")  # for find jack.dll

import pylase as ol

def find_obs_virtual_camera():
    obs_cameras = [x for x in enumerate_cameras() if x.name == 'OBS Virtual Camera']
    if len(obs_cameras) == 0:
        return None
    else:
        return obs_cameras[0]

class VideoApp:
    def __init__(self, root):
        self.cap = None

        self.root = root
        self.root.title("OpenLase Realtime Tracer")

        self.video_label = Label(root)
        self.video_label.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.status_var = tk.StringVar()
        self.status_var.set("起動中...")
        self.status_bar = Label(root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        if len(sys.argv) < 2:
            camera_number = 'obs'
        else:
            camera_number = sys.argv[1]

        filename = None
        camera_backend = None
        open_params = []

        try:
            camera_number = int(camera_number)
        except ValueError:
            if str(camera_number).lower() != 'obs':
                filename = camera_number
                camera_number = None
            else:
                obs = find_obs_virtual_camera()
                if obs is None:
                    camera_number = 0
                    self.update_status(f"OBS Virtual Camera が見つかりませんでした。デフォルトカメラを使用します。")
                else:
                    print(f"OBS Virtual camera found (index={obs.index}, backend={obs.backend}).", file=sys.stderr)
                    camera_number = obs.index
                    camera_backend = obs.backend
                    self.update_status(f"OBS Virtual Camera を使用しています。 (Index: {obs.index})")

        if len(sys.argv) >= 4:
            param = sys.argv[2:4]
            try:
                w, h = map(int, param)
            except ValueError:
                print(f"Can not convert to integer: {', '.join(param)}", file=sys.stderr)
                sys.exit(1)
            else:
                open_params = [cv2.CAP_PROP_FRAME_WIDTH, w, cv2.CAP_PROP_FRAME_HEIGHT, h]

        if filename is not None:
            self.cap = cv2.VideoCapture(filename)
        else:
            self.cap = cv2.VideoCapture(camera_number, camera_backend, params=open_params)

        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if not self.cap.isOpened():
            error_msg = f"Error: Cannot open camera {camera_number}."
            print(error_msg, file=sys.stderr)
            self.update_status(error_msg)
            messagebox.showerror("カメラエラー", error_msg)
            sys.exit(1)
        else:
            print(f"カメラ解像度: {self.width}x{self.height}")

        # pylaseの初期化
        if ol.init(3, 200000) < 0:
            error_msg = "Error: Failed to initialize pylase."
            print(error_msg, file=sys.stderr)
            self.update_status(error_msg)
            messagebox.showerror("pylase エラー", error_msg)
            sys.exit(1)
        else:
            self.update_status("pylase が正常に初期化されました。")

        self.total_points = 0
        self.min_rate = 5

        self.params = ol.RenderParams()
        self.rate = 48000
        self.params.rate = self.rate
        self.params.render_flags = ol.RENDER_GRAYSCALE
        self.params.on_speed = 2 / 60.0
        self.params.off_speed = 1 / 30.0
        self.params.min_length = 15
        self.params.start_wait = 15
        self.params.end_wait = 25
        self.params.flatness = 0.00001
        self.params.max_framelen = self.rate / self.min_rate
        self.params.snap = 1/120.0  # temporary
        self.params.start_dwell = 0
        self.params.end_dwell = 0
        self.params.corner_dwell = 0
        self.params.curve_dwell = 0
        self.params.curve_angle = math.cos(30 * (math.pi / 180.0))

        ol.setRenderParams(self.params)  # TODO Remove this line

        self.tracer = None
        self.overscan = 5
        self.start_time = time.time()
        self.frame_count = 0
        self.fps = 0

        # パラメータコントロールのフレームを右側に表示
        self.control_frame = Frame(root)
        self.control_frame.pack(side=tk.RIGHT, fill=tk.Y)

        # コントロール上部フレームを作成
        self.top_control_frame = Frame(self.control_frame)
        self.top_control_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        self.top_control_frame.columnconfigure(0, weight=1)  # 左側の列を拡張

        # modeを選択するラジオボタン用の変数
        self.mode_var = StringVar(value="CANNY")

        # アプリケーションを終了するボタンを作成
        self.quit_button = Button(self.top_control_frame, text="終了", command=self.on_closing)
        self.quit_button.grid(row=0, column=1, sticky='e', pady=10)  # 右寄せで配置

        # mode選択のラジオボタンを追加
        self.mode_label = Label(self.top_control_frame, text="モード:")
        self.mode_label.grid(row=1, column=0, sticky='w', pady=5)

        self.mode_trace_canny = Radiobutton(
            self.top_control_frame,
            text="CANNY",
            variable=self.mode_var,
            value="CANNY",
            command=self.update_tracer_mode
        )
        self.mode_trace_canny.grid(row=1, column=1, sticky='e')

        self.mode_threshold = Radiobutton(
            self.top_control_frame,
            text="THRESHOLD",
            variable=self.mode_var,
            value="THRESHOLD",
            command=self.update_tracer_mode
        )
        self.mode_threshold.grid(row=2, column=1, sticky='e')

        # **use_color オプションを制御するチェックボックスを追加**
        self.use_color_var = tk.IntVar(value=1)  # 1: True, 0: False
        self.use_color_checkbox = Checkbutton(
            self.top_control_frame,
            text="カラーを使用",
            variable=self.use_color_var
        )
        self.use_color_checkbox.grid(row=3, column=0, columnspan=2, sticky='w', pady=5)

        # コントロール下部左側のフレームを作成
        self.left_control_frame = Frame(self.control_frame)
        self.left_control_frame.grid(row=1, column=0, padx=5, pady=5, sticky="n")

        # コントロール下部右側のフレームを作成
        self.right_control_frame = Frame(self.control_frame)
        self.right_control_frame.grid(row=1, column=1, padx=5, pady=5, sticky="n")

        def create_slider(frame_type, label, from_, to, resolution, initial_value):
            parent = self.left_control_frame if frame_type == 0 else self.right_control_frame
            slider = Scale(parent, from_=from_, to=to, resolution=resolution, orient=HORIZONTAL, label=label, length=200)
            slider.set(initial_value)
            slider.pack()
            return slider

        # スライダーコントロールを左側と右側の列に追加
        self.sigma_scale = create_slider(0, "Blur", 0.1, 5.0, 0.1, 1.1)
        self.threshold_scale = create_slider(0, "Threshold1", 0, 500, 1, 40)
        self.threshold2_scale = create_slider(0, "Threshold2", 0, 500, 1, 140)
        self.on_speed_scale = create_slider(0, "On Speed", 0.01, 1.0, 0.01, self.params.on_speed)
        self.off_speed_scale = create_slider(0, "Off Speed", 0.01, 1.0, 0.01, self.params.off_speed)
        self.flatness_scale = create_slider(0, "Flatness", 0.00001, 0.1, 0.00001, self.params.flatness)

        self.min_length_scale = create_slider(1, "Min size", 1, 100, 1, self.params.min_length)
        self.start_wait_scale = create_slider(1, "Start Wait", 0, 100, 1, self.params.start_wait)
        self.end_wait_scale = create_slider(1, "End Wait", 0, 100, 1, self.params.end_wait)
        self.start_dwell_scale = create_slider(1, "Start Dwell", 0, 100, 1, self.params.start_dwell)
        self.end_dwell_scale = create_slider(1, "End Dwell", 0, 100, 1, self.params.end_dwell)
        self.corner_dwell_scale = create_slider(1, "Corner Dwell", 0, 100, 1, self.params.corner_dwell)
        self.curve_dwell_scale = create_slider(1, "Curve Dwell", 0, 100, 1, self.params.curve_dwell)
        self.snap_scale = create_slider(1, "Snap", 0, 100, 1, 5)
        self.min_rate_scale = create_slider(1, "Min. Rate", 1, 30, 1, self.min_rate)
        self.curve_angle_scale = create_slider(1, "Curve Angle", 0, 1, 0.01, self.params.curve_angle)
        self.decimate_scale = create_slider(0, "Decimate", 1, 10, 1, 1)
        self.overscan_scale = create_slider(0, "Overscan", 0, 100, 1, 5)

        # 設定の保存と読み込み用のボタンを追加
        self.save_button = Button(self.control_frame, text="設定を保存", command=self.save_settings)
        self.save_button.grid(row=2, column=0, padx=5, pady=5, sticky='ew')

        self.load_button = Button(self.control_frame, text="設定を読み込み", command=self.load_settings)
        self.load_button.grid(row=2, column=1, padx=5, pady=5, sticky='ew')

        # ビデオループを開始
        self.update_video()

    def update_status(self, message):
        self.status_var.set(message)

    def save_settings(self):
        settings = {
            "sigma_scale": self.sigma_scale.get(),
            "threshold_scale": self.threshold_scale.get(),
            "threshold2_scale": self.threshold2_scale.get(),
            "on_speed_scale": self.on_speed_scale.get(),
            "off_speed_scale": self.off_speed_scale.get(),
            "flatness_scale": self.flatness_scale.get(),
            "min_length_scale": self.min_length_scale.get(),
            "start_wait_scale": self.start_wait_scale.get(),
            "end_wait_scale": self.end_wait_scale.get(),
            "start_dwell_scale": self.start_dwell_scale.get(),
            "end_dwell_scale": self.end_dwell_scale.get(),
            "corner_dwell_scale": self.corner_dwell_scale.get(),
            "curve_dwell_scale": self.curve_dwell_scale.get(),
            "snap_scale": self.snap_scale.get(),
            "min_rate_scale": self.min_rate_scale.get(),
            "curve_angle_scale": self.curve_angle_scale.get(),
            "decimate_scale": self.decimate_scale.get(),
            "overscan_scale": self.overscan_scale.get(),  # 追加
            "mode_var": self.mode_var.get(),
            "use_color_var": self.use_color_var.get()  # 追加
        }

        file_path = filedialog.asksaveasfilename(defaultextension=".json",
                                                 filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                                                 title="設定を保存するファイルを選択")
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(settings, f, indent=4)
                self.update_status(f"設定を保存しました: {file_path}")
            except Exception as e:
                error_msg = f"設定の保存に失敗しました: {e}"
                print(error_msg, file=sys.stderr)
                self.update_status(error_msg)
                messagebox.showerror("保存エラー", error_msg)

    def load_settings(self):
        file_path = filedialog.askopenfilename(defaultextension=".json",
                                               filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                                               title="設定を読み込むファイルを選択")
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    settings = json.load(f)

                # スライダーとモードの設定を適用
                self.sigma_scale.set(settings.get("sigma_scale", 1.2))
                self.threshold_scale.set(settings.get("threshold_scale", 40))
                self.threshold2_scale.set(settings.get("threshold2_scale", 140))
                self.on_speed_scale.set(settings.get("on_speed_scale", 2 / 60.0))
                self.off_speed_scale.set(settings.get("off_speed_scale", 1 / 30.0))
                self.flatness_scale.set(settings.get("flatness_scale", 0.00001))
                self.min_length_scale.set(settings.get("min_length_scale", 14))
                self.start_wait_scale.set(settings.get("start_wait_scale", 8))
                self.end_wait_scale.set(settings.get("end_wait_scale", 3))
                self.start_dwell_scale.set(settings.get("start_dwell_scale", 0))
                self.end_dwell_scale.set(settings.get("end_dwell_scale", 0))
                self.corner_dwell_scale.set(settings.get("corner_dwell_scale", 0))
                self.curve_dwell_scale.set(settings.get("curve_dwell_scale", 0))
                self.snap_scale.set(settings.get("snap_scale", 1/120.0))
                self.min_rate_scale.set(settings.get("min_rate_scale", 15))
                self.curve_angle_scale.set(settings.get("curve_angle_scale", math.cos(30 * (math.pi / 180.0))))
                self.decimate_scale.set(settings.get("decimate_scale", 1))
                self.overscan_scale.set(settings.get("overscan_scale", 5))  # 追加
                self.mode_var.set(settings.get("mode_var", "CANNY"))
                self.use_color_var.set(settings.get("use_color_var", 1))  # 追加

                self.update_status(f"設定を読み込みました: {file_path}")
            except Exception as e:
                error_msg = f"設定の読み込みに失敗しました: {e}"
                print(error_msg, file=sys.stderr)
                self.update_status(error_msg)
                messagebox.showerror("読み込みエラー", error_msg)

    def update_tracer_mode(self):
        mode = self.mode_var.get()
        if self.tracer is not None:
            if mode == "CANNY":
                self.tracer.mode = ol.TRACE_CANNY
            elif mode == "THRESHOLD":
                self.tracer.mode = ol.TRACE_THRESHOLD
            else:
                warning_msg = f"Warning: Unknown mode {mode}"
                print(warning_msg, file=sys.stderr)
                self.update_status(warning_msg)

    def update_video(self):
        try:
            maxd = self.width if self.width > self.height else self.height
            aspect = self.width / self.height
            iaspect = 1/aspect;

            # スライダーの値を取得してパラメータを更新
            self.params.on_speed = self.on_speed_scale.get()
            self.params.off_speed = self.off_speed_scale.get()
            self.params.min_length = self.min_length_scale.get()
            self.params.start_wait = self.start_wait_scale.get()
            self.params.end_wait = self.end_wait_scale.get()
            self.params.flatness = self.flatness_scale.get()
            self.params.max_framelen = self.rate / self.min_rate_scale.get()
            self.params.snap = (self.snap_scale.get() * 2) / maxd
            self.params.start_dwell = self.start_dwell_scale.get()
            self.params.end_dwell = self.end_dwell_scale.get()
            self.params.corner_dwell = self.corner_dwell_scale.get()
            self.params.curve_dwell = self.curve_dwell_scale.get()
            self.params.curve_angle = self.curve_angle_scale.get()
            self.overscan = self.overscan_scale.get()

            ol.setRenderParams(self.params)

            ol.loadIdentity()
            if aspect > 1:
                ol.setScissor((-1, -iaspect), (1, iaspect))
                ol.scale((1, iaspect))
            else:
                ol.setScissor((-aspect, -1), (aspect, 1))
                ol.scale((aspect, 1))

            ol.scale((1 + self.overscan/100.0, 1 + self.overscan/100.0))
            ol.translate((-1.0, 1.0))
            ol.scale((2.0 / self.width, -2.0 / self.height))

            # FPS計算
            self.frame_count += 1
            curr_time = time.time()
            elapsed_time = curr_time - self.start_time
            if elapsed_time >= 1.0:
                self.fps = self.frame_count / elapsed_time
                self.frame_count = 0
                self.start_time = curr_time
                s = f"FPS: {self.fps:.2f}, Pts: {self.total_points}"

                info = ol.getFrameInfo()
                if info.resampled_points:
                    s += f", Rp: {info.resampled_points}, Bp: {info.resampled_blacks}"
                if info.padding_points:
                    s += f", Pad {info.padding_points}"

                self.update_status(s)
                print(s)

            # フレーム読み込み
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image_rgb = Image.fromarray(frame)

                # Tk 上に表示
                img_width, img_height = image_rgb.size
                ratio = min(320 / img_width, 240 / img_height)
                new_size = (int(img_width * ratio), int(img_height * ratio))
                resized_image = image_rgb.resize(new_size)

                imgtk = ImageTk.PhotoImage(image=resized_image)
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)

                # pylaseのトレース
                im = image_rgb.convert('I')
                if self.tracer is None:
                    width, height = im.size
                    self.tracer = ol.Tracer(width, height)
                    self.update_tracer_mode()  # 初期モードを設定
                    self.tracer.threshold = self.threshold_scale.get()
                    self.tracer.threshold2 = self.threshold2_scale.get()
                    self.tracer.sigma = self.sigma_scale.get()

                # スライダーの値をトレーサーに適用
                if self.tracer is not None:
                    self.tracer.threshold = self.threshold_scale.get()
                    self.tracer.threshold2 = self.threshold2_scale.get()
                    self.tracer.sigma = self.sigma_scale.get()

                s = im.tobytes('raw', 'I')
                if len(s) == (self.width * self.height * 4):
                    s = s[::4]  # XXX workaround PIL bug

                objects = self.tracer.trace(s)

                # **use_color オプションをUIから取得**
                use_color = self.use_color_var.get()  # 0 or 1

                if use_color:
                    color_search_pixels = 1
                else:
                    color_search_pixels = 0

                # DECIMATEの値をスライダーから取得
                decimate = self.decimate_scale.get()

                # 画像データをNumPy配列に変換（カラー処理のため）
                frame_np = np.array(image_rgb)

                for o in objects:
                    if len(o) > decimate:
                        ol.begin(ol.POINTS)
                        for j, point in enumerate(o):
                            if j % decimate == 0:
                                p_x, p_y = point

                                # 各ポイント周辺のカラー情報を取得
                                if use_color:
                                    r1, g1, b1 = frame_np[p_y, p_x] / 255.0

                                    h, s, v = colorsys.rgb_to_hsv(r1, g1, b1)

                                    gamma = 0.2  # 1 未満だと s2,v2 寄りになる
                                    s1 = s
                                    v1 = 0.8 + 0.2 * abs(v * 2 - 1.0)
                                    s2 = 1
                                    v2 = 0.8 + 0.2 * v
                                    f = s ** gamma
                                    s = (1 - f) * s1 + f * s2
                                    v = (1 - f) * v1 + f * v2

                                    # 調整後のHSVをRGBに再変換
                                    r, g, b = colorsys.hsv_to_rgb(h, s, v)
                                    r = int(r * 255)
                                    g = int(g * 255)
                                    b = int(b * 255)

                                    # RGBからカラーコードを生成
                                    color = (r << 16) | (g << 8) | b

                                    ol.vertex(point, color)
                                else:
                                    ol.vertex(point, ol.C_WHITE)

                                self.total_points += 1
                        ol.end()

                ol.renderFrame(80)
            else:
                warning_msg = "Warning: Failed to read frame from camera."
                print(warning_msg, file=sys.stderr)
                self.update_status(warning_msg)

            self.root.after(50, self.update_video)

        except Exception as e:
            error_msg = f"Error: During update: {e}"
            print(error_msg, file=sys.stderr)
            self.update_status(error_msg)
            self.root.after(1000, self.update_video)

    def on_closing(self):
        self.cleanup()
        self.root.destroy()

    def cleanup(self):
        if self.cap is not None:
            if self.cap.isOpened():
                self.cap.release()
        cv2.destroyAllWindows()

    def __del__(self):
        self.cleanup()

# メインウィンドウを作成し、VideoAppのインスタンスを作成
root = tk.Tk()
app = VideoApp(root)

# Tkinterのイベントループを実行
try:
    root.mainloop()
except KeyboardInterrupt:
    app.cleanup()
    root.destroy()
    sys.exit(0)
