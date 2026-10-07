import tkinter as tk
from tkinter import messagebox, filedialog
import ctypes
from ctypes import wintypes
import time, csv, json
from datetime import datetime
from pathlib import Path

BG="#808080"; BLACK="#000000"; WHITE="#FFFFFF"
REFERENCE_HEIGHT_CM=30.0; TEST_FLOOR_HEIGHT_CM=25.5
SMALL_CM=2.0*TEST_FLOOR_HEIGHT_CM/REFERENCE_HEIGHT_CM
LARGE_CM=20.0*TEST_FLOOR_HEIGHT_CM/REFERENCE_HEIGHT_CM
SMALL_SEC=3.0; EXPAND_SEC=2.0; LARGE_SEC=3.0; FRAME_MS=16
CAL_TARGET_CM=10.0; MAX_TRIALS=5; DEFAULT_PX_PER_CM=34.0
VK_F12=0x7B; KEYEVENTF_KEYUP=0x0002
APP_DIR=Path.home()/"Documents"/"LoomingTest_Data"
APP_DIR.mkdir(parents=True,exist_ok=True)
SETTINGS_FILE=APP_DIR/"looming_settings.json"
DEFAULT_CSV_DIR=APP_DIR

try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try: ctypes.windll.user32.SetProcessDPIAware()
    except Exception: pass

def press_f12():
    ctypes.windll.user32.keybd_event(VK_F12,0,0,0)
    time.sleep(0.02)
    ctypes.windll.user32.keybd_event(VK_F12,0,KEYEVENTF_KEYUP,0)

def get_monitors():
    out=[]
    PROC=ctypes.WINFUNCTYPE(ctypes.c_int,ctypes.c_ulong,ctypes.c_ulong,ctypes.POINTER(wintypes.RECT),ctypes.c_double)
    def cb(hm,hdc,r,data):
        q=r.contents; out.append((q.left,q.top,q.right,q.bottom)); return 1
    ctypes.windll.user32.EnumDisplayMonitors(0,0,PROC(cb),0)
    return out

def load_settings():
    obj={}
    try:
        with SETTINGS_FILE.open("r",encoding="utf-8") as f:
            obj=json.load(f)
    except Exception:
        pass
    try:
        scale=float(obj.get("pixels_per_cm",DEFAULT_PX_PER_CM))
        if scale<=0: scale=DEFAULT_PX_PER_CM
    except Exception:
        scale=DEFAULT_PX_PER_CM
    folder=Path(obj.get("csv_folder",str(DEFAULT_CSV_DIR)))
    if not folder.exists():
        folder=DEFAULT_CSV_DIR
    return scale, folder

def save_settings(scale, folder):
    with SETTINGS_FILE.open("w",encoding="utf-8") as f:
        json.dump({
            "pixels_per_cm":scale,
            "csv_folder":str(folder),
            "saved_at":datetime.now().isoformat(timespec="seconds")
        },f,indent=2)


def safe_mouse_id(value):
    value=value.strip()
    bad='<>:"/\\|?*'
    for ch in bad:
        value=value.replace(ch,"_")
    return value


class App:
    def __init__(self,root):
        self.root=root; root.title("Looming test ver.2"); root.geometry("670x760+40+25"); root.minsize(520,500); root.protocol("WM_DELETE_WINDOW",self.quit)

        # Scrollable control panel for PCs with small screens or 125/150% scaling.
        self.outer=tk.Frame(root)
        self.outer.pack(fill="both",expand=True)
        self.scroll_canvas=tk.Canvas(self.outer,highlightthickness=0)
        self.vscroll=tk.Scrollbar(self.outer,orient="vertical",command=self.scroll_canvas.yview)
        self.scroll_canvas.configure(yscrollcommand=self.vscroll.set)
        self.vscroll.pack(side="right",fill="y")
        self.scroll_canvas.pack(side="left",fill="both",expand=True)

        self.panel=tk.Frame(self.scroll_canvas)
        self.panel_window=self.scroll_canvas.create_window((0,0),window=self.panel,anchor="nw")

        def _panel_configure(event):
            self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))
        def _canvas_configure(event):
            self.scroll_canvas.itemconfigure(self.panel_window,width=event.width)
        def _wheel(event):
            if event.delta:
                self.scroll_canvas.yview_scroll(int(-1*(event.delta/120)),"units")

        self.panel.bind("<Configure>",_panel_configure)
        self.scroll_canvas.bind("<Configure>",_canvas_configure)
        self.scroll_canvas.bind_all("<MouseWheel>",_wheel)
        root.bind_all("<Prior>",lambda e:self.scroll_canvas.yview_scroll(-1,"pages"))
        root.bind_all("<Next>",lambda e:self.scroll_canvas.yview_scroll(1,"pages"))
        root.bind_all("<Home>",lambda e:self.scroll_canvas.yview_moveto(0))
        root.bind_all("<End>",lambda e:self.scroll_canvas.yview_moveto(1))
        ui=self.panel
        self.px_per_cm,self.csv_dir=load_settings(); self.mouse_id=""; self.running=False; self.recording=False; self.trial=0; self.disk=None
        self.time_zero=None; self.stim_start=None; self.clock_job=None
        self.make_log()

        tk.Label(ui,text="Looming test ver.2",font=("Arial",22,"bold")).pack(pady=(12,2))
        tk.Label(ui,text=f"25.5 cm setup: {SMALL_CM:.1f} cm → {LARGE_CM:.1f} cm (30 cm reference × 0.85)",font=("Arial",10)).pack()
        self.status=tk.Label(ui,text="GRAY / READY",font=("Arial",17,"bold")); self.status.pack(pady=(8,2))
        self.trial_lab=tk.Label(ui,text="Trial: 0 / 5",font=("Arial",14)); self.trial_lab.pack()

        cal=tk.LabelFrame(ui,text="1. Physical-size calibration",font=("Arial",11,"bold"),padx=10,pady=8); cal.pack(fill="x",padx=22,pady=(9,5))
        tk.Label(cal,text="Show the 10-cm bar, measure it with a ruler, enter the result, then Apply.",font=("Arial",9)).pack(anchor="w")
        tk.Button(cal,text="SHOW 10 cm CALIBRATION BAR",command=self.show_cal,font=("Arial",10,"bold")).pack(pady=5)
        row=tk.Frame(cal); row.pack()
        tk.Label(row,text="Measured (cm):").pack(side="left")
        self.measure=tk.Entry(row,width=8,justify="center"); self.measure.insert(0,"10.0"); self.measure.pack(side="left",padx=6)
        tk.Button(row,text="APPLY & SAVE",command=self.apply_cal).pack(side="left")
        self.scale_lab=tk.Label(cal,text=f"Saved scale: {self.px_per_cm:.3f} px/cm",font=("Arial",9)); self.scale_lab.pack(pady=(5,0))
        tk.Button(cal,text="RETURN TO GRAY",command=self.clear_gray).pack(pady=(5,0))

        animal=tk.LabelFrame(ui,text="2. Animal",font=("Arial",11,"bold"),padx=10,pady=8); animal.pack(fill="x",padx=22,pady=5)
        ar=tk.Frame(animal); ar.pack(anchor="w")
        tk.Label(ar,text="Mouse ID:",font=("Arial",10,"bold")).pack(side="left")
        self.mouse_entry=tk.Entry(ar,width=24,font=("Arial",11)); self.mouse_entry.pack(side="left",padx=8)
        tk.Label(animal,text="Example: ICR01   (required before recording)",font=("Arial",9)).pack(anchor="w",pady=(4,0))

        rec=tk.LabelFrame(ui,text="3. Bandicam recording / Time 0",font=("Arial",11,"bold"),padx=10,pady=8); rec.pack(fill="x",padx=22,pady=5)
        tk.Label(rec,text="Open Bandicam first. Keep Record/Stop hotkey = F12.\nSTART sends F12 and defines the app's Time 0.",justify="left",font=("Arial",9)).pack(anchor="w")
        self.rec_btn=tk.Button(rec,text="START RECORDING / TIME 0",command=self.start_recording,font=("Arial",13,"bold"),height=2); self.rec_btn.pack(fill="x",pady=(7,4))
        self.timer=tk.Label(rec,text="Video time: --:--:--.---",font=("Consolas",16,"bold")); self.timer.pack()
        self.rec_lab=tk.Label(rec,text="NOT STARTED",font=("Arial",10,"bold")); self.rec_lab.pack()

        exp=tk.LabelFrame(ui,text="4. Experiment",font=("Arial",11,"bold"),padx=10,pady=8); exp.pack(fill="x",padx=22,pady=5)
        self.trigger_btn=tk.Button(exp,text="TRIGGER LOOMING",command=self.trigger,font=("Arial",16,"bold"),height=2,state="disabled"); self.trigger_btn.pack(fill="x",pady=(4,5))
        self.note=tk.Label(exp,text="Start Bandicam / Time 0 before triggering.",font=("Arial",10)); self.note.pack()
        self.last=tk.Label(exp,text="Last looming onset: --",font=("Consolas",11)); self.last.pack(pady=3)
        tk.Label(exp,text="F9 = Time 0   |   SPACE = Looming   |   Ctrl+R = New session   |   ESC = Quit",font=("Arial",9)).pack(pady=3)
        tk.Button(exp,text="NEW SESSION / RESET  (Ctrl+R)",command=self.new_session).pack(pady=4)

        self.stop_btn=tk.Button(ui,text="STOP BANDICAM RECORDING (F12)",command=self.stop_recording,font=("Arial",10,"bold"),state="disabled"); self.stop_btn.pack(pady=(7,3))
        data=tk.LabelFrame(ui,text="CSV data",font=("Arial",10,"bold"),padx=8,pady=6); data.pack(fill="x",padx=22,pady=(6,3))
        self.folder_lab=tk.Label(data,text=f"Folder: {self.csv_dir}",font=("Arial",8),justify="left",wraplength=560); self.folder_lab.pack(anchor="w")
        tk.Button(data,text="SELECT CSV FOLDER",command=self.select_csv_folder,font=("Arial",9,"bold")).pack(pady=4)
        self.file_lab=tk.Label(data,text=f"CSV: {self.log_file.name}",font=("Arial",8),justify="left",wraplength=560); self.file_lab.pack(anchor="w")
        tk.Label(ui,text="Software hotkey synchronization; not hardware/frame-locked.\nScroll with mouse wheel or the bar on the right.",font=("Arial",8)).pack(pady=(0,10))

        root.bind_all("<F9>",self.start_recording); root.bind_all("<space>",self.trigger); root.bind_all("<Control-r>",self.new_session); root.bind_all("<Control-R>",self.new_session); root.bind_all("<Escape>",self.quit)
        self.stim=tk.Toplevel(root); self.stim.overrideredirect(True); self.stim.configure(bg=BG)
        self.canvas=tk.Canvas(self.stim,bg=BG,highlightthickness=0,bd=0); self.canvas.pack(fill="both",expand=True)
        root.after(500,self.move_to_dell)

    @staticmethod
    def fmt(s):
        if s is None:return "--:--:--.---"
        s=max(0,s); h=int(s//3600); m=int((s%3600)//60); sec=s%60
        return f"{h:02d}:{m:02d}:{sec:06.3f}"

    def elapsed(self): return None if self.time_zero is None else time.perf_counter()-self.time_zero

    def update_clock(self):
        if self.time_zero is not None:self.timer.config(text=f"Video time: {self.fmt(self.elapsed())}")
        self.clock_job=self.root.after(30,self.update_clock)

    def make_log(self):
        self.session=datetime.now().strftime("%Y%m%d_%H%M%S"); self.csv_dir.mkdir(parents=True,exist_ok=True)
        prefix=(safe_mouse_id(self.mouse_id)+"_") if self.mouse_id else ""
        self.log_file=self.csv_dir/f"{prefix}looming_{self.session}.csv"
        with self.log_file.open("w",newline="",encoding="utf-8-sig") as f:
            csv.writer(f).writerow(["mouse_id","session_id","trial","event","video_time_s","video_time_hms","local_datetime","pixels_per_cm","monitor_to_floor_cm","small_diameter_cm","large_diameter_cm"])

    def log(self,event,video_s=None,trial=None):
        if video_s is None:video_s=self.elapsed()
        with self.log_file.open("a",newline="",encoding="utf-8-sig") as f:
            csv.writer(f).writerow([self.mouse_id,self.session,self.trial if trial is None else trial,event,"" if video_s is None else f"{video_s:.6f}","" if video_s is None else self.fmt(video_s),datetime.now().isoformat(timespec="milliseconds"),f"{self.px_per_cm:.6f}",TEST_FLOOR_HEIGHT_CM,f"{SMALL_CM:.3f}",f"{LARGE_CM:.3f}"])

    def select_csv_folder(self):
        if self.recording or self.running:
            messagebox.showwarning("Session active","Choose the CSV folder before starting recording.")
            return
        chosen=filedialog.askdirectory(
            title="Select folder for Looming CSV files",
            initialdir=str(self.csv_dir)
        )
        if not chosen:
            return
        self.csv_dir=Path(chosen)
        save_settings(self.px_per_cm,self.csv_dir)
        # Create a fresh empty session CSV in the newly selected folder.
        self.make_log()
        self.folder_lab.config(text=f"Folder: {self.csv_dir}")
        self.file_lab.config(text=f"CSV: {self.log_file.name}")

    def move_to_dell(self):
        ms=get_monitors()
        if len(ms)<2: messagebox.showerror("Display","Second monitor not detected. Use Windows Extend mode."); return
        l,t,r,b=max(ms,key=lambda x:x[0]); self.stim.geometry(f"{r-l}x{b-t}+{l}+{t}"); self.stim.update_idletasks(); self.stim.lift(); self.root.lift(); self.root.focus_force(); self.clear_gray()

    def show_cal(self):
        if self.running:return
        self.canvas.delete("all"); self.canvas.configure(bg=BG); w=self.canvas.winfo_width(); h=self.canvas.winfo_height(); L=CAL_TARGET_CM*self.px_per_cm; y=h/2; x1=(w-L)/2; x2=(w+L)/2
        self.canvas.create_rectangle(x1,y-12,x2,y+12,fill=WHITE,outline=WHITE); self.canvas.create_line(x1,y-35,x1,y+35,fill=WHITE,width=3); self.canvas.create_line(x2,y-35,x2,y+35,fill=WHITE,width=3); self.status.config(text="CALIBRATION MODE")

    def apply_cal(self):
        try:m=float(self.measure.get())
        except ValueError:messagebox.showerror("Invalid value","Enter the measured length in cm.");return
        if m<=0:messagebox.showerror("Invalid value","Value must be > 0.");return
        self.px_per_cm*=CAL_TARGET_CM/m; save_settings(self.px_per_cm,self.csv_dir); self.scale_lab.config(text=f"Saved scale: {self.px_per_cm:.3f} px/cm"); self.show_cal()

    def start_recording(self,event=None):
        if self.recording or self.running:return "break"
        mid=self.mouse_entry.get().strip()
        if not mid:
            messagebox.showwarning("Mouse ID required","Enter the Mouse ID before starting recording.")
            self.mouse_entry.focus_set()
            return "break"
        self.mouse_id=mid
        # Create the actual session CSV only after Mouse ID is known.
        self.make_log()
        self.file_lab.config(text=f"CSV: {self.log_file.name}")
        self.mouse_entry.config(state="disabled")
        # Define Time 0 immediately before dispatching Bandicam's F12 hotkey.
        self.time_zero=time.perf_counter()
        try:press_f12()
        except Exception as e:self.time_zero=None;messagebox.showerror("Bandicam",str(e));return "break"
        self.recording=True; self.log("VIDEO_TIME_ZERO",0.0,0); self.rec_btn.config(text="RECORDING / TIME 0 SET",state="disabled"); self.stop_btn.config(state="normal"); self.rec_lab.config(text="RECORDING"); self.trigger_btn.config(state="normal"); self.note.config(text="Ready for Trial 1")
        if self.clock_job is None:self.update_clock()
        self.root.focus_force(); return "break"

    def stop_recording(self):
        if not self.recording:return
        if self.running:messagebox.showwarning("Stimulus running","Wait until looming finishes.");return
        self.log("VIDEO_STOP_COMMAND",self.elapsed())
        try:press_f12()
        except Exception as e:messagebox.showerror("Bandicam",str(e));return
        self.recording=False; self.stop_btn.config(state="disabled"); self.trigger_btn.config(state="disabled"); self.rec_lab.config(text="RECORDING STOPPED"); self.note.config(text="Start a new session for another recording.")

    def clear_gray(self):
        if self.running:return
        self.canvas.delete("all"); self.canvas.configure(bg=BG); self.disk=None; self.status.config(text="GRAY / READY")
        if self.recording and self.trial<MAX_TRIALS:self.trigger_btn.config(state="normal");self.note.config(text=f"Ready for Trial {self.trial+1}")
        elif self.trial>=MAX_TRIALS:self.trigger_btn.config(state="disabled");self.note.config(text="5 / 5 trials completed")
        else:self.trigger_btn.config(state="disabled")

    def draw_disk(self,cm):
        d=cm*self.px_per_cm; r=d/2; w=self.canvas.winfo_width(); h=self.canvas.winfo_height(); cx=w/2; cy=h/2; box=(cx-r,cy-r,cx+r,cy+r)
        if self.disk is None:self.disk=self.canvas.create_oval(*box,fill=BLACK,outline=BLACK,width=0)
        else:self.canvas.coords(self.disk,*box)

    def trigger(self,event=None):
        if self.running or not self.recording or self.time_zero is None or self.trial>=MAX_TRIALS:return "break"
        self.running=True; self.trial+=1; onset=self.elapsed(); self.stim_start=time.perf_counter(); self.trial_lab.config(text=f"Trial: {self.trial} / 5"); self.status.config(text="LOOMING RUNNING"); self.note.config(text="Stimulus in progress"); self.trigger_btn.config(state="disabled"); self.last.config(text=f"Last looming onset: {self.fmt(onset)}")
        self.canvas.delete("all"); self.canvas.configure(bg=BG); self.disk=None; self.log("LOOMING_ONSET",onset); self.draw_disk(SMALL_CM); self.animate(); return "break"

    def animate(self):
        s=time.perf_counter()-self.stim_start; t1=SMALL_SEC; t2=t1+EXPAND_SEC; t3=t2+LARGE_SEC
        if s<t1:d=SMALL_CM
        elif s<t2:d=SMALL_CM+(s-t1)/EXPAND_SEC*(LARGE_CM-SMALL_CM)
        elif s<t3:d=LARGE_CM
        else:self.log("LOOMING_END",self.elapsed());self.running=False;self.clear_gray();self.root.focus_force();return
        self.draw_disk(d); self.root.after(FRAME_MS,self.animate)

    def new_session(self,event=None):
        if self.running:return "break"
        if self.recording:messagebox.showwarning("Recording active","Stop Bandicam recording first.");return "break"
        if self.trial>0 or self.time_zero is not None:
            if not messagebox.askyesno("New session","Reset Time 0 and trial count?"):return "break"
        self.trial=0; self.time_zero=None; self.mouse_id=""
        self.mouse_entry.config(state="normal"); self.mouse_entry.delete(0,"end"); self.mouse_entry.focus_set()
        if self.clock_job is not None:
            try:self.root.after_cancel(self.clock_job)
            except Exception:pass
            self.clock_job=None
        self.make_log(); self.trial_lab.config(text="Trial: 0 / 5"); self.timer.config(text="Video time: --:--:--.---"); self.last.config(text="Last looming onset: --"); self.rec_lab.config(text="NOT STARTED"); self.rec_btn.config(text="START RECORDING / TIME 0",state="normal"); self.stop_btn.config(state="disabled"); self.trigger_btn.config(state="disabled"); self.note.config(text="Start Bandicam / Time 0 before triggering."); self.folder_lab.config(text=f"Folder: {self.csv_dir}"); self.file_lab.config(text=f"CSV: {self.log_file.name}"); self.clear_gray(); return "break"

    def quit(self,event=None):
        if self.recording and not messagebox.askyesno("Recording active","Bandicam may still be recording. Close anyway?"):return "break"
        try:self.stim.destroy()
        except Exception:pass
        self.root.destroy(); return "break"

if __name__=="__main__":
    root=tk.Tk(); App(root); root.mainloop()
