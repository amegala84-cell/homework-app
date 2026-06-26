# homework_manager_final_complete_fixed_v2.py
# Full updated file (v2) — includes:
# - Confirm-password fields for all change-password dialogs
# - Admin: removed "View Students" action on teacher cards
# - Delete confirmations require typing DELETE
# - Teacher: inline edit for students (inside the card), plus view, block, delete
# - Teacher: can view/edit/delete homework only for today and future dates
# - simple_dialog upgraded to support on_ok/on_cancel callbacks (Approach 1)
#
# Date: 2025-10-26 (with dialog callback support added)

import json
import os
import sys
import ctypes
import calendar
from datetime import datetime, date
from functools import partial

from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.uix.screenmanager import Screen
from kivy.uix.image import Image
from kivy.uix.widget import Widget

from kivymd.app import MDApp
from kivymd.uix.card import MDCard
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.textfield import MDTextField, MDTextFieldRect

# Desktop test window size (remove or change on mobile)
Window.size = (420, 780)

DATA_FILE = "homework_data.json"
DEFAULT_PASSWORD = "admin"

# ------------------ Helpers ------------------
def ensure_data_file():
    if not os.path.exists(DATA_FILE):
        base = {
            "owner": {"username": "owner", "password": DEFAULT_PASSWORD},
            "admins": {},
            "teachers": {},
            "students": {}
        }
        with open(DATA_FILE, "w") as f:
            json.dump(base, f, indent=4)
    else:
        try:
            with open(DATA_FILE, "r") as f:
                d = json.load(f)
        except Exception:
            try:
                os.rename(DATA_FILE, DATA_FILE + ".corrupt")
            except Exception:
                pass
            ensure_data_file()
            return
        changed = False
        if "owner" not in d:
            d["owner"] = {"username": "owner", "password": DEFAULT_PASSWORD}
            changed = True
        for k in ("admins", "teachers", "students"):
            if k not in d or not isinstance(d[k], dict):
                d[k] = {}
                changed = True
        if changed:
            with open(DATA_FILE, "w") as f:
                json.dump(d, f, indent=4)

def load_data():
    ensure_data_file()
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(d):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(d, f, indent=4)
    os.replace(tmp, DATA_FILE)

def simple_dialog(title, text, on_ok=None, on_cancel=None, ok_text="OK", cancel_text="Cancel"):
    dialog = MDDialog(title=title, text=text, size_hint=(0.9, None), buttons=[])

    def _do_cancel(inst):
        try:
            if callable(on_cancel):
                on_cancel()
        except Exception:
            pass
        dialog.dismiss()

    def _do_ok(inst):
        try:
            if callable(on_ok):
                on_ok()
        except Exception:
            pass
        dialog.dismiss()

    dialog.buttons = [
        MDFlatButton(text=cancel_text, on_release=_do_cancel),
        MDRaisedButton(text=ok_text, on_release=_do_ok)
    ]
    dialog.open()

def colored_palette(idx):
    palette = [
        (0.81, 0.91, 1.00, 1.0),  # pale sky blue (#CFE9FF)
        (0.93, 0.84, 1.00, 1.0),  # soft lavender (#E7D6FF)
        (1.00, 0.87, 0.87, 1.0),  # gentle rose (#FFDDEE)
        (1.00, 0.95, 0.80, 1.0),  # warm cream (#FFF3CC)
        (0.84, 1.00, 0.91, 1.0),  # minty (#D6FFE7)
        (0.90, 0.97, 1.00, 1.0),  # very light aqua (#E6F7FF)
    ]
    return palette[idx % len(palette)]

# Date helpers: accept multiple input formats, store/display as DD-MM-YY
def parse_date_flexible(s):
    s = (s or "").strip()
    if not s:
        return None
    # Try several known formats
    for fmt in ("%d-%m-%y", "%d-%m-%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    # Try common human formats
    for sep in ("-", "/", "."):
        parts = s.split(sep)
        if len(parts) == 3:
            try:
                # try day-month-year with 2 or 4 digit year
                day = int(parts[0]); month = int(parts[1]); year = int(parts[2])
                if year < 100:
                    year += 2000
                return datetime(year, month, day)
            except Exception:
                pass
    return None

def fmt_ddmmyy(dt):
    if not dt:
        return ""
    return dt.strftime("%d-%m-%y")

def is_today_or_future(dd_mm_yy_str):
    dt = parse_date_flexible(dd_mm_yy_str)
    if not dt:
        return False
    # compare date only
    return dt.date() >= date.today()

# ------------------ KV ------------------
KV = r"""
#:import utils kivy.utils
ScreenManager:
    LoginScreen:
    OwnerScreen:
    AdminScreen:
    TeacherScreen:
    StudentScreen:

<LoginScreen>:
    name: "login"
    MDBoxLayout:
        orientation: "vertical"
        padding: dp(14)
        spacing: dp(10)
        canvas.before:
            Color:
                rgba: 0.86,0.95,0.98,1
            Rectangle:
                pos: self.x, self.y
                size: self.width*0.5, self.height
            Color:
                rgba: 0.98,0.92,0.95,1
            Rectangle:
                pos: self.x + self.width*0.5, self.y
                size: self.width*0.5, self.height
            Color:
                rgba: 1,1,1,0.6
            Rectangle:
                pos: self.pos
                size: self.size
        MDBoxLayout:
            size_hint_y: None
            height: dp(68)
            padding: dp(10), dp(8)
            MDLabel:
                text: "[color=#0b66b2][b]Home[/b][/color][color=#7c4dff][b]work[/b][/color]  [color=#ff5ea9][b]Manager[/b][/color]"
                markup: True
                halign: "left"
                valign: "middle"
                font_style: "H5"
            MDLabel:
                id: dt_login
                text: ""
                size_hint_x: None
                width: dp(140)
                halign: "right"
                valign: "middle"
                theme_text_color: "Secondary"
        MDBoxLayout:
            size_hint_y: None
            height: dp(44)
            MDTextField:
                id: login_user
                hint_text: "Username"
                mode: "rectangle"
        MDBoxLayout:
            size_hint_y: None
            height: dp(48)
            MDTextField:
                id: login_pass
                hint_text: "Password"
                password: True
                mode: "rectangle"
            MDIconButton:
                id: pass_toggle
                icon: "eye-off"
                user_font_size: "20sp"
                tooltip_text: "Show / hide password"
                on_release:
                    login_pass.password = not login_pass.password
                    self.icon = "eye-off" if login_pass.password else "eye"
        MDBoxLayout:
            size_hint_y: None
            height: dp(52)
            spacing: dp(8)
            MDRaisedButton:
                text: "Login"
                md_bg_color: (0.35,0.68,0.95,1)
                on_release: root.do_login()
            MDFlatButton:
                text: "Exit to Login"   # on login screen this simply clears fields
                on_release:
                    login_user.text = ""
                    login_pass.text = ""
        Widget:
            size_hint_y: None
            height: dp(6)
        MDLabel:
            text: "© 2026 Homework Manager by Sakshain"
            halign: "center"
            theme_text_color: "Custom"
            text_color: (0.2,0.2,0.2,0.7)
            font_style: "Caption"

<OwnerScreen>:
    name: "owner"
    MDBoxLayout:
        orientation: "vertical"
        padding: dp(12)
        spacing: dp(8)
        canvas.before:
            Color:
                rgba: 0.86,0.95,0.98,1
            Rectangle:
                pos: self.x, self.y
                size: self.width*0.6, self.height
            Color:
                rgba: 0.98,0.92,0.95,1
            Rectangle:
                pos: self.x + self.width*0.6, self.y
                size: self.width*0.4, self.height
            Color:
                rgba: 1,1,1,0.6
            Rectangle:
                pos: self.pos
                size: self.size
        MDBoxLayout:
            size_hint_y: None
            height: dp(68)
            padding: dp(10), dp(8)
            MDLabel:
                text: "[color=#0b66b2][b]Owner[/b][/color]  [color=#7c4dff][b]Panel[/b][/color]"
                markup: True
                halign: "left"
                valign: "middle"
                font_style: "H6"
            MDLabel:
                id: dt_owner
                text: ""
                size_hint_x: None
                width: dp(160)
                halign: "right"
                valign: "middle"
                theme_text_color: "Secondary"
        MDGridLayout:
            cols: 2
            adaptive_height: True
            spacing: dp(8)
            MDTextField:
                id: owner_admin_user
                hint_text: "Admin Username *"
                mode: "rectangle"
            MDTextField:
                id: owner_admin_name
                hint_text: "Admin Name *"
                mode: "rectangle"
            MDTextField:
                id: owner_admin_school
                hint_text: "School Name *"
                mode: "rectangle"
            MDTextField:
                id: owner_admin_contact1
                hint_text: "Contact 1 *"
                input_filter: "int"
                mode: "rectangle"
            MDTextField:
                id: owner_admin_contact2
                hint_text: "Contact 2"
                input_filter: "int"
                mode: "rectangle"
            MDTextField:
                id: owner_admin_address
                hint_text: "Address *"
                mode: "rectangle"
            MDTextField:
                id: owner_admin_mail
                hint_text: "Email ID *"
                mode: "rectangle"
        MDBoxLayout:
            size_hint_y: None
            height: dp(48)
            spacing: dp(8)
            MDRaisedButton:
                id: owner_create_update_btn
                text: "Create Admin"
                md_bg_color: (0.3,0.7,0.95,1)
                on_release: root.create_or_update_admin()
            MDFlatButton:
                id: owner_cancel_edit_btn
                text: "Cancel Edit"
                on_release: root.cancel_admin_edit()
                opacity: 0
                disabled: True
            MDRaisedButton:
                text: "Change Owner Password"
                md_bg_color: (0.9,0.6,0.95,1)
                on_release: root.change_owner_password()
            MDRaisedButton:
                text: "Exit"
                on_release: app.root.current = "login"
        MDTextField:
            id: owner_search_admin
            hint_text: "Search admins (live)"
            mode: "rectangle"
            on_text: root.filter_admins(self.text)
        MDLabel:
            text: "Admins"
            halign: "left"
            font_style: "Subtitle1"
            theme_text_color: "Custom"
            text_color: 0.15,0.15,0.15,0.95
        ScrollView:
            MDGridLayout:
                id: admins_grid
                cols: 1
                adaptive_height: True
                spacing: dp(12)
                padding: dp(8)

<AdminScreen>:
    name: "admin"
    MDBoxLayout:
        orientation: "vertical"
        padding: dp(12)
        spacing: dp(8)
        canvas.before:
            Color:
                rgba: 0.86,0.95,0.98,1
            Rectangle:
                pos: self.x, self.y
                size: self.width*0.6, self.height
            Color:
                rgba: 0.98,0.92,0.95,1
            Rectangle:
                pos: self.x + self.width*0.6, self.y
                size: self.width*0.4, self.height
            Color:
                rgba: 1,1,1,0.6
            Rectangle:
                pos: self.pos
                size: self.size
        MDBoxLayout:
            size_hint_y: None
            height: dp(68)
            padding: dp(10), dp(8)
            MDLabel:
                text: "[color=#0b66b2][b]Admin[/b][/color]  [color=#7c4dff][b]Panel[/b][/color]"
                markup: True
                halign: "left"
                valign: "middle"
                font_style: "H6"
            MDLabel:
                id: dt_admin
                text: ""
                size_hint_x: None
                width: dp(160)
                halign: "right"
                valign: "middle"
                theme_text_color: "Secondary"
        MDGridLayout:
            cols: 2
            adaptive_height: True
            spacing: dp(8)
            MDTextField:
                id: admin_teacher_user
                hint_text: "Teacher Username *"
                mode: "rectangle"
            MDTextField:
                id: admin_teacher_name
                hint_text: "Teacher Name *"
                mode: "rectangle"
            MDTextField:
                id: admin_teacher_grade
                hint_text: "Grade *"
                mode: "rectangle"
            MDTextField:
                id: admin_teacher_section
                hint_text: "Section *"
                mode: "rectangle"
            MDTextField:
                id: admin_teacher_classroom
                hint_text: "Classroom No *"
                mode: "rectangle"
            MDTextField:
                id: admin_teacher_contact
                hint_text: "Contact *"
                input_filter: "int"
                mode: "rectangle"
            MDTextField:
                id: admin_teacher_mail
                hint_text: "Email ID *"
                mode: "rectangle"
        MDBoxLayout:
            size_hint_y: None
            height: dp(48)
            spacing: dp(8)
            MDRaisedButton:
                id: admin_create_update_btn
                text: "Add Teacher"
                md_bg_color: (0.3,0.7,0.95,1)
                on_release: root.create_or_update_teacher()
            MDFlatButton:
                id: admin_cancel_edit_btn
                text: "Cancel Edit"
                on_release: root.cancel_teacher_edit()
                opacity: 0
                disabled: True
            MDRaisedButton:
                text: "Change Admin Password"
                md_bg_color: (0.9,0.6,0.95,1)
                on_release: root.change_admin_password()
            MDRaisedButton:
                text: "Exit"
                on_release: app.root.current = "login"
        MDTextField:
            id: admin_search_teacher
            hint_text: "Search teachers (live)"
            mode: "rectangle"
            on_text: root.filter_teachers(self.text)
        MDLabel:
            text: "Teachers"
            halign: "left"
            font_style: "Subtitle1"
            theme_text_color: "Custom"
            text_color: 0.15,0.15,0.15,0.95
        ScrollView:
            MDGridLayout:
                id: teachers_grid
                cols: 1
                adaptive_height: True
                spacing: dp(12)
                padding: dp(8)

<TeacherScreen>:
    name: "teacher"
    ScrollView:
        do_scroll_x: False
        do_scroll_y: True
        MDGridLayout:
            cols: 1
            size_hint_y: None
            height: self.minimum_height
            padding: dp(12)
            spacing: dp(8)
            canvas.before:
                Color:
                    rgba: 0.86,0.95,0.98,1
                Rectangle:
                    pos: self.x, self.y
                    size: self.width*0.6, self.height
                Color:
                    rgba: 0.98,0.92,0.95,1
                Rectangle:
                    pos: self.x + self.width*0.4, self.y
                    size: self.width*0.4, self.height
                Color:
                    rgba: 1,1,1,0.6
                Rectangle:
                    pos: self.pos
                    size: self.size
            MDBoxLayout:
                size_hint_y: None
                height: dp(68)
                padding: dp(10), dp(8)
                MDLabel:
                    text: "[color=#0b66b2][b]Teacher[/b][/color]  [color=#7c4dff][b]Panel[/b][/color]"
                    markup: True
                    halign: "left"
                    valign: "middle"
                    font_style: "H6"
                MDLabel:
                    id: dt_teacher
                    text: ""
                    size_hint_x: None
                    width: dp(160)
                    halign: "right"
                    valign: "middle"
                    theme_text_color: "Secondary"
            MDGridLayout:
                cols: 2
                adaptive_height: True
                spacing: dp(8)
                MDTextField:
                    id: stu_user
                    hint_text: "Student Username *"
                    mode: "rectangle"
                MDTextField:
                    id: stu_reg
                    hint_text: "Reg. No *"
                    mode: "rectangle"
                MDTextField:
                    id: stu_contact
                    hint_text: "Contact *"
                    input_filter: "int"
                    mode: "rectangle"
                MDTextField:
                    id: stu_dob
                    hint_text: "DOB (DD-MM-YY) *"
                    mode: "rectangle"
            MDBoxLayout:
                size_hint_y: None
                height: dp(48)
                spacing: dp(8)
                MDRaisedButton:
                    id: add_student_btn
                    text: "Add Student"
                    md_bg_color: (0.3,0.7,0.95,1)
                    on_release: root.add_student()
                MDRaisedButton:
                    text: "Change Teacher Password"
                    md_bg_color: (0.9,0.6,0.95,1)
                    on_release: root.change_teacher_password()
                MDRaisedButton:
                    text: "Exit"
                    on_release: app.root.current = "login"
            MDSeparator:
                height: dp(1)
            MDLabel:
                text: "Add Homework"
                halign: "left"
                font_style: "Subtitle1"
                theme_text_color: "Custom"
                text_color: 0.15,0.15,0.15,0.95
            MDBoxLayout:
                size_hint_y: None
                height: dp(56)
                spacing: dp(8)
                MDTextField:
                    id: hw_date
                    hint_text: "Homework Date"
                    mode: "rectangle"
                    readonly: True
                    helper_text: "Tap the calendar icon to pick a date"
                    helper_text_mode: "on_focus"
                MDIconButton:
                    icon: "calendar-month"
                    user_font_size: "24sp"
                    theme_text_color: "Primary"
                    on_release: root.open_date_picker('hw_date')
            MDBoxLayout:
                size_hint_y: None
                height: dp(56)
                spacing: dp(8)
                MDTextField:
                    id: hw_submit
                    hint_text: "Submit Date"
                    mode: "rectangle"
                    readonly: True
                    helper_text: "Tap the calendar icon to pick a date"
                    helper_text_mode: "on_focus"
                MDIconButton:
                    icon: "calendar-month"
                    user_font_size: "24sp"
                    theme_text_color: "Primary"
                    on_release: root.open_date_picker('hw_submit')
            MDTextFieldRect:
                id: hw_details
                hint_text: "Homework Details (use newlines)"
                size_hint_y: None
                height: dp(140)
            MDBoxLayout:
                size_hint_y: None
                height: dp(48)
                spacing: dp(8)
                MDRaisedButton:
                    id: add_hw_btn
                    text: "Add Homework (All your students)"
                    md_bg_color: (0.35,0.68,0.95,1)
                    on_release: root.add_homework()
                MDRaisedButton:
                    text: "View Students"
                    md_bg_color: (0.5,0.5,0.75,1)
                    on_release: root.view_students()
                MDRaisedButton:
                    id: hw_attach_photo_btn
                    text: "Attach/Take Photo"
                    md_bg_color: (0.7,0.6,0.95,1)
                    on_release: root.attach_or_take_photo()
            MDTextField:
                id: teacher_search_student
                hint_text: "Search students (live)"
                mode: "rectangle"
                on_text: root.filter_students(self.text)
            MDLabel:
                id: hw_photo_label
                text: "No photo attached"
                size_hint_y: None
                height: dp(24)
                theme_text_color: "Secondary"
            MDLabel:
                text: "Students"
                halign: "left"
                font_style: "Subtitle1"
                theme_text_color: "Custom"
                text_color: 0.15,0.15,0.15,0.95
            ScrollView:
                MDGridLayout:
                    id: students_grid
                    cols: 1
                    size_hint_y: None
                    height: self.minimum_height
                    adaptive_height: True
                    spacing: dp(12)
                    padding: dp(8)
            MDSeparator:
                height: dp(1)
            MDBoxLayout:
                id: student_detail_panel
                orientation: "vertical"
                size_hint_y: None
                height: dp(120)
                padding: dp(6)
                spacing: dp(6)

<StudentScreen>:
    name: "student"
    MDBoxLayout:
        id: student_root
        orientation: "vertical"
        padding: dp(12)
        spacing: dp(8)
        canvas.before:
            Color:
                rgba: 0.86,0.95,0.98,1
            Rectangle:
                pos: self.x, self.y
                size: self.width*0.6, self.height
            Color:
                rgba: 0.98,0.92,0.95,1
            Rectangle:
                pos: self.x + self.width*0.6, self.y
                size: self.width*0.4, self.height
            Color:
                rgba: 1,1,1,0.6
            Rectangle:
                pos: self.pos
                size: self.size
        MDBoxLayout:
            size_hint_y: None
            height: dp(68)
            padding: dp(10), dp(8)
            MDLabel:
                text: "[color=#0b66b2][b]Student[/b][/color]  [color=#7c4dff][b]Portal[/b][/color]"
                markup: True
                halign: "left"
                valign: "middle"
                font_style: "H6"
            MDLabel:
                id: dt_student
                text: ""
                size_hint_x: None
                width: dp(160)
                halign: "right"
                valign: "middle"
                theme_text_color: "Secondary"
        MDLabel:
            id: student_welcome
            text: ""
            halign: "left"
            size_hint_y: None
            height: dp(36)
            theme_text_color: "Primary"
        MDGridLayout:
            cols: 1
            adaptive_height: True
            spacing: dp(8)
            MDTextField:
                id: student_user_field
                hint_text: "Enter your username (or leave blank if logged in)"
                mode: "rectangle"
        MDBoxLayout:
            size_hint_y: None
            height: dp(48)
            spacing: dp(8)
            MDRaisedButton:
                text: "Load Homeworks"
                md_bg_color: (0.35,0.68,0.95,1)
                on_release: root.load_and_show_homework()
            MDRaisedButton:
                text: "Change Student Password"
                md_bg_color: (0.9,0.6,0.95,1)
                on_release: root.change_student_password()
            MDRaisedButton:
                text: "Exit"
                on_release: app.root.current = "login"
        MDTextField:
            id: student_search_hw
            hint_text: "Search your homework (live)"
            mode: "rectangle"
            on_text: root.filter_student_homework(self.text)
        ScrollView:
            MDGridLayout:
                id: student_hw_grid
                cols: 1
                adaptive_height: True
                spacing: dp(12)
                padding: dp(8)
"""

# ------------------ Screens & Logic ------------------
class LoginScreen(Screen):
    def show_help(self):
        help_text = (
            "[b]User creation & default credentials[/b]\n\n"
            "• Owner: created automatically "
            "• Admin: created by Owner "
            "• Teacher: created by Admin "
            "• Student: created by Teacher "
            "[b]Hierarchy & cascade rules[/b]\n"
            "• If Owner deletes an Admin, that Admin's Teachers and their Students are also deleted.\n"
            "• If Admin deletes a Teacher, that Teacher's students become unassigned (teacher=None).\n\n"
            "Passwords: each user can change their own password (single visible field, no confirm)."
        )
        MDDialog(title="Help — User creation & cascade rules", text=help_text, size_hint=(0.9, None)).open()

    def do_login(self):
        u = (self.ids.login_user.text or "").strip()
        p = (self.ids.login_pass.text or "").strip()
        if not u or not p:
            simple_dialog("Error", "Enter username and password")
            return
        data = load_data()
        owner = data.get("owner", {})
        if u.lower() == owner.get("username","owner").lower() and p == owner.get("password", DEFAULT_PASSWORD):
            self.manager.current = "owner"
            return
        # Admins
        for a, info in data.get("admins", {}).items():
            if u.lower() == a.lower() and info.get("password") == p:
                if info.get("blocked"):
                    simple_dialog("Blocked", "This admin is blocked"); return
                scr = self.manager.get_screen("admin")
                scr.current_admin = a
                self.manager.current = "admin"
                return
        # Teachers
        for t, info in data.get("teachers", {}).items():
            if u.lower() == t.lower() and info.get("password") == p:
                if info.get("blocked"):
                    simple_dialog("Blocked", "This teacher is blocked"); return
                scr = self.manager.get_screen("teacher")
                scr.current_teacher = t.strip()
                self.manager.current = "teacher"
                return
        # Students
        for s, info in data.get("students", {}).items():
            if u.lower() == s.lower() and info.get("password") == p:
                if info.get("blocked"):
                    simple_dialog("Blocked", "This student is blocked"); return
                scr = self.manager.get_screen("student")
                scr.current_student = s
                self.manager.current = "student"
                return
        simple_dialog("Login Failed", "Incorrect username or password")

# ---------- Owner ----------
class OwnerScreen(Screen):
    editing_admin = None

    def on_enter(self, *args):
        Clock.schedule_once(lambda dt: self.populate_admins_grid(), 0.02)
        self.update_datetime_label()

    def update_datetime_label(self, *l):
        lbl = self.ids.get("dt_owner")
        if lbl:
            lbl.text = datetime.now().strftime("%d-%m-%y %H:%M:%S")
        Clock.schedule_once(self.update_datetime_label, 1)

    def create_or_update_admin(self):
        if self.editing_admin:
            # update
            user = self.editing_admin
            i = self.ids
            name = (i.owner_admin_name.text or "").strip()
            school = (i.owner_admin_school.text or "").strip()
            c1 = (i.owner_admin_contact1.text or "").strip()
            c2 = (i.owner_admin_contact2.text or "").strip()
            addr = (i.owner_admin_address.text or "").strip()
            mail = (i.owner_admin_mail.text or "").strip()
            if not all([name, school, c1, addr, mail]):
                simple_dialog("Error", "All required fields (*) must be filled"); return
            data = load_data()
            if user not in data.get("admins", {}):
                simple_dialog("Error", "Admin not found"); return
            a = data["admins"][user]
            a.update({"name": name, "school": school, "contact1": c1, "contact2": c2, "address": addr, "mail": mail})
            save_data(data)
            simple_dialog("Success", f"Admin '{user}' updated")
            self.cancel_admin_edit()
            self.populate_admins_grid()
        else:
            # create new
            i = self.ids
            user = (i.owner_admin_user.text or "").strip()
            name = (i.owner_admin_name.text or "").strip()
            school = (i.owner_admin_school.text or "").strip()
            c1 = (i.owner_admin_contact1.text or "").strip()
            c2 = (i.owner_admin_contact2.text or "").strip()
            addr = (i.owner_admin_address.text or "").strip()
            mail = (i.owner_admin_mail.text or "").strip()
            if not all([user, name, school, c1, addr, mail]):
                simple_dialog("Error", "All required fields (*) must be filled"); return
            data = load_data()
            if any(user.lower() == u.lower() for u in data.get("admins", {})):
                simple_dialog("Error", "Admin username already exists"); return
            data.setdefault("admins", {})[user] = {
                "name": name, "school": school, "contact1": c1, "contact2": c2,
                "address": addr, "mail": mail, "password": DEFAULT_PASSWORD, "blocked": False
            }
            save_data(data)
            simple_dialog("Success", f"Admin '{user}' created with default password '{DEFAULT_PASSWORD}'")
            for idn in ("owner_admin_user", "owner_admin_name", "owner_admin_school", "owner_admin_contact1", "owner_admin_contact2", "owner_admin_address", "owner_admin_mail"):
                self.ids[idn].text = ""
            self.populate_admins_grid()

    def cancel_admin_edit(self, *args):
        self.editing_admin = None
        btn = self.ids.get("owner_create_update_btn")
        cancel_btn = self.ids.get("owner_cancel_edit_btn")
        if btn:
            btn.text = "Create Admin"
        if cancel_btn:
            cancel_btn.opacity = 0
            cancel_btn.disabled = True
        # clear fields
        for idn in ("owner_admin_user", "owner_admin_name", "owner_admin_school", "owner_admin_contact1", "owner_admin_contact2", "owner_admin_address", "owner_admin_mail"):
            self.ids[idn].text = ""
            self.ids[idn].disabled = False

    def populate_admins_grid(self, filter_text=""):
        grid = self.ids.admins_grid
        grid.clear_widgets()
        data = load_data()
        items = list(data.get("admins", {}).items())
        f = (filter_text or "").strip().lower()
        if f:
            items = [(k, v) for k, v in items if f in k.lower() or f in v.get("name","").lower() or f in v.get("school","").lower() or f in v.get("mail","").lower()]
        if not items:
            grid.add_widget(MDLabel(text="No admins yet", halign="center", theme_text_color="Primary"))
            return
        for idx, (username, info) in enumerate(items):
            card = MDCard(size_hint_y=None, height=dp(130), padding=dp(10), radius=[12])
            card.md_bg_color = colored_palette(idx)
            box = MDBoxLayout(orientation="vertical", spacing=dp(6), padding=dp(6))
            box.add_widget(MDLabel(text=username, bold=True, font_style="Subtitle1", size_hint_y=None, height=dp(28)))
            box.add_widget(MDLabel(text=f"{info.get('name','')} — {info.get('school','')}\n{info.get('mail','')}", theme_text_color="Secondary"))
            btns = MDBoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))
            btns.add_widget(MDRaisedButton(text="Edit", on_release=partial(self.edit_admin, username)))
            btns.add_widget(MDFlatButton(text="Block" if not info.get("blocked") else "Unblock", on_release=partial(self.toggle_block_admin, username)))
            btns.add_widget(MDFlatButton(text="Delete", on_release=partial(self.confirm_delete_admin, username)))
            box.add_widget(btns)
            card.add_widget(box)
            grid.add_widget(card)

    def filter_admins(self, text):
        self.populate_admins_grid(filter_text=text)

    def edit_admin(self, username, *args):
        data = load_data()
        info = data.get("admins", {}).get(username)
        if not info:
            simple_dialog("Error", "Admin not found"); return
        # fill fields in owner screen
        self.ids.owner_admin_user.text = username
        self.ids.owner_admin_user.disabled = True
        self.ids.owner_admin_name.text = info.get("name","")
        self.ids.owner_admin_school.text = info.get("school","")
        self.ids.owner_admin_contact1.text = info.get("contact1","")
        self.ids.owner_admin_contact2.text = info.get("contact2","")
        self.ids.owner_admin_address.text = info.get("address","")
        self.ids.owner_admin_mail.text = info.get("mail","")
        self.editing_admin = username
        btn = self.ids.get("owner_create_update_btn")
        cancel_btn = self.ids.get("owner_cancel_edit_btn")
        if btn:
            btn.text = "Update Admin"
        if cancel_btn:
            cancel_btn.opacity = 1
            cancel_btn.disabled = False

    def confirm_delete_admin(self, username, *args):
        # New: require user type DELETE to confirm
        content = MDBoxLayout(orientation="vertical", spacing=8, padding=8)
        content.add_widget(MDLabel(text=f"Type 'DELETE' to confirm deletion of admin '{username}'", size_hint_y=None, height=dp(48)))
        confirm_field = MDTextField(hint_text="Type DELETE here", mode="rectangle")
        content.add_widget(confirm_field)
        dialog = MDDialog(title="Confirm Delete Admin", type="custom", content_cls=content, size_hint=(0.9, None), buttons=[])
        def do_delete(inst):
            if (confirm_field.text or "").strip().upper() != "DELETE":
                simple_dialog("Error", "You must type DELETE to confirm"); return
            data = load_data()
            teachers = [t for t, ti in data.get("teachers", {}).items() if ti.get("admin") == username]
            for t in teachers:
                studs = [s for s, si in data.get("students", {}).items() if si.get("teacher") == t]
                for s in studs:
                    data["students"].pop(s, None)
                data["teachers"].pop(t, None)
            data["admins"].pop(username, None)
            save_data(data)
            dialog.dismiss()
            simple_dialog("Deleted", f"Admin '{username}' deleted; their teachers and students removed")
            self.populate_admins_grid()
        dialog.buttons = [
            MDFlatButton(text="Cancel", on_release=lambda inst: dialog.dismiss()),
            MDFlatButton(text="Delete", on_release=do_delete)
        ]
        dialog.open()

    def toggle_block_admin(self, username, *args):
        data = load_data()
        admin = data.get("admins", {}).get(username)
        if not admin:
            simple_dialog("Error", "Admin not found"); return
        target = not admin.get("blocked", False)
        admin["blocked"] = target
        # cascade: block/unblock their teachers and students
        for t, ti in data.get("teachers", {}).items():
            if ti.get("admin") == username:
                ti["blocked"] = target
                for s, si in data.get("students", {}).items():
                    if si.get("teacher") == t:
                        si["blocked"] = target
        save_data(data)
        simple_dialog("Updated", f"Admin '{username}' {'blocked' if target else 'unblocked'} (cascade applied)")
        self.populate_admins_grid()

    def change_owner_password(self):
        # standardized password dialog with a mobile-friendly Change button
        content = MDBoxLayout(orientation="vertical", spacing=8, padding=12, size_hint_y=None, height=dp(220))
        newp = MDTextField(hint_text="New Owner Password", password=True)
        confirm = MDTextField(hint_text="Confirm New Password", password=True)
        info = MDLabel(text="Fill both fields and press Change", theme_text_color="Secondary", size_hint_y=None, height=dp(24))
        content.add_widget(newp)
        content.add_widget(confirm)
        content.add_widget(info)
        dialog = MDDialog(title="Change Owner Password", type="custom", content_cls=content, size_hint=(0.9, None))
        def do_change(*args):
            npw = (newp.text or "")
            cpw = (confirm.text or "")
            if not npw:
                simple_dialog("Error", "Password cannot be empty")
                return
            if npw != cpw:
                simple_dialog("Error", "Passwords do not match")
                return
            data = load_data()
            data["owner"]["password"] = npw
            save_data(data)
            dialog.dismiss()
            simple_dialog("Success", "Owner password changed")
        confirm.bind(on_text_validate=do_change)
        # mobile-friendly in-dialog Change button (full-width)
        content.add_widget(MDRaisedButton(text="Change", on_release=do_change, size_hint_y=None, height=dp(44)))
        dialog.buttons = [MDFlatButton(text="Cancel", on_release=lambda inst: dialog.dismiss())]
        dialog.open()

# ---------- Admin ----------
class AdminScreen(Screen):
    current_admin = None
    editing_teacher = None

    def on_enter(self, *args):
        Clock.schedule_once(lambda dt: self.populate_teachers_grid(), 0.02)
        self.update_datetime()

    def update_datetime(self, *l):
        lbl = self.ids.get("dt_admin")
        if lbl:
            lbl.text = datetime.now().strftime("%d-%m-%y %H:%M:%S")
        Clock.schedule_once(self.update_datetime, 1)

    def create_or_update_teacher(self):
        i = self.ids
        if self.editing_teacher:
            # update existing teacher
            username = self.editing_teacher
            name = (i.admin_teacher_name.text or "").strip()
            grade = (i.admin_teacher_grade.text or "").strip()
            section = (i.admin_teacher_section.text or "").strip()
            classroom = (i.admin_teacher_classroom.text or "").strip()
            contact = (i.admin_teacher_contact.text or "").strip()
            mail = (i.admin_teacher_mail.text or "").strip()
            if not all([name, grade, section, classroom, contact, mail]):
                simple_dialog("Error", "All fields are mandatory"); return
            data = load_data()
            if username not in data.get("teachers", {}):
                simple_dialog("Error", "Teacher not found"); return
            t = data["teachers"][username]
            t.update({"name": name, "grade": grade, "section": section, "classroom": classroom, "contact": contact, "mail": mail})
            save_data(data)
            simple_dialog("Success", f"Teacher '{username}' updated")
            self.cancel_teacher_edit()
            self.populate_teachers_grid()
        else:
            username = (i.admin_teacher_user.text or "").strip()
            name = (i.admin_teacher_name.text or "").strip()
            grade = (i.admin_teacher_grade.text or "").strip()
            section = (i.admin_teacher_section.text or "").strip()
            classroom = (i.admin_teacher_classroom.text or "").strip()
            contact = (i.admin_teacher_contact.text or "").strip()
            mail = (i.admin_teacher_mail.text or "").strip()
            if not all([username, name, grade, section, classroom, contact, mail]):
                simple_dialog("Error", "All fields are mandatory"); return
            data = load_data()
            if any(username.lower() == u.lower() for u in data.get("teachers", {})):
                simple_dialog("Error", "Teacher username exists"); return
            data.setdefault("teachers", {})[username] = {
                "name": name, "grade": grade, "section": section, "classroom": classroom,
                "contact": contact, "mail": mail, "password": DEFAULT_PASSWORD, "blocked": False, "admin": self.current_admin
            }
            save_data(data)
            simple_dialog("Success", f"Teacher '{username}' added with default password '{DEFAULT_PASSWORD}'")
            for idn in ("admin_teacher_user","admin_teacher_name","admin_teacher_grade","admin_teacher_section","admin_teacher_classroom","admin_teacher_contact","admin_teacher_mail"):
                self.ids[idn].text = ""
            self.populate_teachers_grid()

    def cancel_teacher_edit(self, *args):
        self.editing_teacher = None
        btn = self.ids.get("admin_create_update_btn")
        cancel_btn = self.ids.get("admin_cancel_edit_btn")
        if btn:
            btn.text = "Add Teacher"
        if cancel_btn:
            cancel_btn.opacity = 0
            cancel_btn.disabled = True
        # clear fields and re-enable user field
        for idn in ("admin_teacher_user","admin_teacher_name","admin_teacher_grade","admin_teacher_section","admin_teacher_classroom","admin_teacher_contact","admin_teacher_mail"):
            self.ids[idn].text = ""
        self.ids.admin_teacher_user.disabled = False

    def populate_teachers_grid(self, filter_admin=None, filter_text=""):
        grid = self.ids.teachers_grid
        grid.clear_widgets()
        data = load_data()
        items = list(data.get("teachers", {}).items())
        # Show only teachers for this admin unless filter_admin explicitly provided
        if filter_admin:
            items = [(k,v) for k,v in items if v.get("admin")==filter_admin]
        else:
            items = [(k,v) for k,v in items if v.get("admin")==self.current_admin]
        f = (filter_text or "").strip().lower()
        if f:
            items = [(k,v) for k,v in items if f in k.lower() or f in v.get("name","").lower() or f in v.get("mail","").lower() or f in v.get("grade","").lower() or f in v.get("section","").lower()]
        if not items:
            grid.add_widget(MDLabel(text="No teachers yet", halign="center", theme_text_color="Primary"))
            return
        for idx, (username, info) in enumerate(items):
            card = MDCard(size_hint_y=None, height=dp(140), padding=dp(10), radius=[12])
            card.md_bg_color = colored_palette(idx)
            box = MDBoxLayout(orientation="vertical", spacing=dp(6), padding=dp(6))
            box.add_widget(MDLabel(text=username, bold=True, font_style="Subtitle1", size_hint_y=None, height=dp(28)))
            box.add_widget(MDLabel(text=f"{info.get('name','')} — Class:{info.get('grade','')} Sec:{info.get('section','')}\n{info.get('mail','')}", theme_text_color="Secondary"))
            btns = MDBoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))
            btns.add_widget(MDRaisedButton(text="Edit", on_release=partial(self.edit_teacher, username)))
            # Removed "View Students" from admin panel as requested
            btns.add_widget(MDFlatButton(text="Block" if not info.get("blocked") else "Unblock", on_release=partial(self.toggle_block_teacher, username)))
            btns.add_widget(MDFlatButton(text="Delete", on_release=partial(self.confirm_delete_teacher, username)))
            box.add_widget(btns)
            card.add_widget(box)
            grid.add_widget(card)

    def filter_teachers(self, text):
        self.populate_teachers_grid(filter_text=text)

    def edit_teacher(self, username, *args):
        data = load_data()
        info = data.get("teachers", {}).get(username)
        if not info:
            simple_dialog("Error", "Teacher not found"); return
        # populate inline fields in admin area for edit (like owner admin edit)
        self.ids.admin_teacher_user.text = username
        self.ids.admin_teacher_user.disabled = True
        self.ids.admin_teacher_name.text = info.get("name","")
        self.ids.admin_teacher_grade.text = info.get("grade","")
        self.ids.admin_teacher_section.text = info.get("section","")
        self.ids.admin_teacher_classroom.text = info.get("classroom","")
        self.ids.admin_teacher_contact.text = info.get("contact","")
        self.ids.admin_teacher_mail.text = info.get("mail","")
        self.editing_teacher = username
        btn = self.ids.get("admin_create_update_btn")
        cancel_btn = self.ids.get("admin_cancel_edit_btn")
        if btn:
            btn.text = "Update Teacher"
        if cancel_btn:
            cancel_btn.opacity = 1
            cancel_btn.disabled = False

    def view_students_of_teacher(self, teacher_username, *args):
        # kept for compatibility but admin no longer shows "View Students" button
        data = load_data()
        students = [(s, si) for s, si in data.get("students", {}).items() if si.get("teacher") == teacher_username]
        if not students:
            dialog = MDDialog(title=f"Students of {teacher_username}", text="No students found for this teacher.", size_hint=(0.9, None))
            dialog.open()
            return
        content = MDBoxLayout(orientation="vertical", spacing=8, padding=8)
        for sname, sinfo in students:
            row = MDBoxLayout(size_hint_y=None, height=dp(40), spacing=8)
            row.add_widget(MDLabel(text=f"{sname} — Reg:{sinfo.get('reg','')}", size_hint_x=0.6))
            btn_view = MDRaisedButton(text="View", size_hint_x=0.25, on_release=partial(self._show_student_detail_dialog, sname))
            row.add_widget(btn_view)
            btn_edit = MDFlatButton(text="Edit", size_hint_x=0.15, on_release=partial(self._show_student_edit_from_admin, sname))
            row.add_widget(btn_edit)
            content.add_widget(row)
        dialog = MDDialog(title=f"Students of {teacher_username}", type="custom", content_cls=content, buttons=[])
        dialog.buttons = [MDFlatButton(text="Close", on_release=lambda inst: dialog.dismiss())]
        dialog.open()

    def _show_student_detail_dialog(self, student_username, *args):
        # popup to show student details (for admin use)
        data = load_data()
        s = data.get("students", {}).get(student_username)
        if not s:
            simple_dialog("Error", "Student not found"); return
        text = (f"Username: {student_username}\nReg: {s.get('reg','')}\nDOB: {s.get('dob','')}\nContact: {s.get('contact','')}\nTeacher: {s.get('teacher')}")
        dialog = MDDialog(title=f"Student: {student_username}", text=text, size_hint=(0.9, None), buttons=[])
        dialog.buttons = [
            MDFlatButton(text="Close", on_release=lambda inst: dialog.dismiss())
        ]
        dialog.open()

    def _show_student_edit_from_admin(self, student_username, *args):
        # Admin can open a quick edit dialog for a student
        data = load_data()
        s = data.get("students", {}).get(student_username)
        if not s:
            simple_dialog("Error", "Student not found"); return
        content = MDBoxLayout(orientation="vertical", spacing=8, padding=8)
        reg = MDTextField(text=s.get("reg",""), hint_text="Reg", mode="rectangle")
        contact = MDTextField(text=s.get("contact",""), hint_text="Contact", input_filter="int", mode="rectangle")
        dob = MDTextField(text=s.get("dob",""), hint_text="DOB (DD-MM-YY)", mode="rectangle")
        content.add_widget(reg); content.add_widget(contact); content.add_widget(dob)
        dialog = MDDialog(title=f"Edit Student: {student_username}", type="custom", content_cls=content, buttons=[])
        dialog.buttons = [
            MDFlatButton(text="Cancel", on_release=lambda inst: dialog.dismiss()),
            MDFlatButton(text="Save", on_release=lambda inst: self._save_student_edit_by_admin(student_username, reg.text, contact.text, dob.text, dialog))
        ]
        dialog.open()

    def _save_student_edit_by_admin(self, username, reg, contact, dob, dialog):
        if not all([username, reg, contact, dob]):
            simple_dialog("Error", "All fields are mandatory"); return
        dt = parse_date_flexible(dob)
        if not dt:
            simple_dialog("Error", "DOB not recognizable"); return
        data = load_data()
        if username not in data.get("students", {}):
            simple_dialog("Error", "Student not found"); dialog.dismiss(); return
        s = data["students"][username]
        s.update({"reg": reg, "contact": contact, "dob": fmt_ddmmyy(dt)})
        save_data(data)
        dialog.dismiss()
        simple_dialog("Success", f"Student '{username}' updated")

    def confirm_delete_teacher(self, username, *args):
        # require typing DELETE to confirm deletion
        content = MDBoxLayout(orientation="vertical", spacing=8, padding=8)
        content.add_widget(MDLabel(text=f"Type 'DELETE' to confirm deletion of teacher '{username}'", size_hint_y=None, height=dp(48)))
        confirm_field = MDTextField(hint_text="Type DELETE here", mode="rectangle")
        content.add_widget(confirm_field)
        dialog = MDDialog(title="Confirm Delete Teacher", type="custom", content_cls=content, size_hint=(0.9, None), buttons=[])
        def do_delete(inst):
            if (confirm_field.text or "").strip().upper() != "DELETE":
                simple_dialog("Error", "You must type DELETE to confirm"); return
            data = load_data()
            for s, si in list(data.get("students", {}).items()):
                if si.get("teacher") == username:
                    si["teacher"] = None
            data["teachers"].pop(username, None)
            save_data(data)
            dialog.dismiss()
            simple_dialog("Deleted", f"Teacher '{username}' deleted; their students are now unassigned")
            self.populate_teachers_grid()
        dialog.buttons = [
            MDFlatButton(text="Cancel", on_release=lambda inst: dialog.dismiss()),
            MDFlatButton(text="Delete", on_release=do_delete)
        ]
        dialog.open()

    def toggle_block_teacher(self, username, *args):
        data = load_data()
        teacher = data.get("teachers", {}).get(username)
        if not teacher:
            simple_dialog("Error", "Teacher not found"); return
        target = not teacher.get("blocked", False)
        teacher["blocked"] = target
        for s, si in data.get("students", {}).items():
            if si.get("teacher") == username:
                si["blocked"] = target
        save_data(data)
        simple_dialog("Updated", f"Teacher '{username}' {'blocked' if target else 'unblocked'}")
        self.populate_teachers_grid()

    def change_admin_password(self):
        content = MDBoxLayout(orientation="vertical", spacing=8, padding=12, size_hint_y=None, height=dp(180))
        newp = MDTextField(hint_text="New Admin Password", password=True)
        confirm = MDTextField(hint_text="Confirm New Password", password=True)
        content.add_widget(newp)
        content.add_widget(confirm)
        dialog = MDDialog(title="Change Admin Password", type="custom", content_cls=content, size_hint=(0.9, None))
        def do_change(inst):
            npw = (newp.text or "")
            cpw = (confirm.text or "")
            if not npw:
                simple_dialog("Error", "Password cannot be empty"); return
            if npw != cpw:
                simple_dialog("Error", "Passwords do not match"); return
            data = load_data()
            if not self.current_admin or self.current_admin not in data.get("admins", {}):
                simple_dialog("Error", "No admin selected"); return
            data["admins"][self.current_admin]["password"] = npw
            save_data(data)
            dialog.dismiss()
            simple_dialog("Success", "Admin password changed")
        info = MDLabel(text="Fill both fields and press Change", theme_text_color="Secondary", size_hint_y=None, height=dp(24))
        content.add_widget(info)
        # add in-dialog full-width Change button for mobile
        content.add_widget(MDRaisedButton(text="Change", on_release=do_change, size_hint_y=None, height=dp(44)))
        dialog.buttons = [MDFlatButton(text="Cancel", on_release=lambda inst: dialog.dismiss())]
        dialog.open()

# ---------- Teacher ----------
class TeacherScreen(Screen):
    current_teacher = None

    def on_enter(self, *args):
        Clock.schedule_once(lambda dt: self.view_students(), 0.02)
        self.update_datetime_label()

    def update_datetime_label(self, *l):
        lbl = self.ids.get("dt_teacher")
        if lbl:
            lbl.text = datetime.now().strftime("%d-%m-%y %H:%M:%S")
        Clock.schedule_once(self.update_datetime_label, 1)

    def open_date_picker(self, field_id):
        today = datetime.now().date()

        def use_builtin_picker():
            MDDatePicker = None
            try:
                from kivymd.uix.picker import MDDatePicker
                MDDatePicker = MDDatePicker
            except Exception:
                try:
                    from kivymd.uix.pickers import MDDatePicker
                    MDDatePicker = MDDatePicker
                except Exception:
                    MDDatePicker = None
            if not MDDatePicker:
                return False

            def on_save(instance, value, date_range):
                fld = self.ids.get(field_id)
                if fld:
                    fld.text = fmt_ddmmyy(value)

            date_picker = MDDatePicker(year=today.year, month=today.month, day=today.day)
            try:
                date_picker.bind(on_save=on_save)
            except Exception:
                try:
                    date_picker.bind(on_save=on_save)
                except Exception:
                    pass
            date_picker.open()
            return True

        if use_builtin_picker():
            return

        state = {
            'year': today.year,
            'month': today.month,
            'selected_day': today.day,
        }

        selected_label = None

        def update_selected(day):
            state['selected_day'] = day
            if selected_label:
                selected_label.text = f"Selected: {fmt_ddmmyy(datetime(state['year'], state['month'], day))}"
            refresh_calendar()

        def apply_selection(*_args):
            try:
                dt = datetime(state['year'], state['month'], state['selected_day'])
            except Exception:
                simple_dialog('Error', 'Please select a valid day')
                return
            fld = self.ids.get(field_id)
            if fld:
                fld.text = fmt_ddmmyy(dt)
            dlg.dismiss()

        def update_month(delta):
            y = state['year']
            m = state['month'] + delta
            if m < 1:
                m = 12
                y -= 1
            elif m > 12:
                m = 1
                y += 1
            state['year'], state['month'] = y, m
            state['selected_day'] = 0
            selected_label.text = 'Selected: None'
            refresh_calendar()

        def goto_today(*_args):
            state['year'], state['month'] = today.year, today.month
            state['selected_day'] = today.day
            selected_label.text = f"Selected: {fmt_ddmmyy(today)}"
            refresh_calendar()

        def refresh_calendar():
            nonlocal selected_label
            content.clear_widgets()

            header = MDBoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8), padding=[0, 0, 0, 0])
            btn_prev = MDIconButton(icon='chevron-left', on_release=lambda inst: update_month(-1))
            btn_next = MDIconButton(icon='chevron-right', on_release=lambda inst: update_month(1))
            title_label = MDLabel(
                text=f"{calendar.month_name[state['month']]} {state['year']}",
                halign='center',
                valign='middle',
                size_hint_x=1,
                theme_text_color='Primary',
                bold=True,
            )
            header.add_widget(btn_prev)
            header.add_widget(title_label)
            header.add_widget(btn_next)
            content.add_widget(header)

            selected_label = MDLabel(
                text=f"Selected: {fmt_ddmmyy(datetime(state['year'], state['month'], state['selected_day']))}" if state['selected_day'] else 'Selected: None',
                halign='center',
                theme_text_color='Secondary',
                size_hint_y=None,
                height=dp(24),
            )
            content.add_widget(selected_label)

            weekday_row = MDGridLayout(cols=7, size_hint_y=None, height=dp(28), spacing=dp(4))
            for wd in ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']:
                weekday_row.add_widget(
                    MDLabel(text=wd, halign='center', theme_text_color='Secondary', font_style='Caption')
                )
            content.add_widget(weekday_row)

            cal_grid = MDGridLayout(cols=7, spacing=dp(4), size_hint_y=None)
            month_weeks = calendar.monthcalendar(state['year'], state['month'])
            cal_grid.height = dp(42) * len(month_weeks)
            for week in month_weeks:
                for day in week:
                    if day == 0:
                        cal_grid.add_widget(MDLabel(text='', size_hint_y=None, height=dp(42)))
                    else:
                        is_today = (
                            state['year'] == today.year and
                            state['month'] == today.month and
                            day == today.day
                        )
                        is_selected = day == state['selected_day'] and state['year'] == today.year and state['month'] == today.month
                        day_btn = MDRaisedButton(
                            text=str(day),
                            size_hint_y=None,
                            height=dp(42),
                            md_bg_color=(0.9, 0.95, 1, 1) if is_selected else (0.98, 0.98, 0.98, 1) if is_today else None,
                            text_color=(0, 0, 0, 1),
                            on_release=lambda inst, d=day: update_selected(d),
                        )
                        cal_grid.add_widget(day_btn)
            content.add_widget(cal_grid)

            footer = MDBoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
            footer.add_widget(MDRaisedButton(text='Today', on_release=goto_today))
            footer.add_widget(MDRaisedButton(text='Set', on_release=apply_selection))
            footer.add_widget(MDFlatButton(text='Cancel', on_release=lambda inst: dlg.dismiss()))
            content.add_widget(footer)

        content = MDBoxLayout(orientation='vertical', spacing=dp(12), padding=dp(12))
        dlg = MDDialog(title='Choose a date', type='custom', content_cls=content, size_hint=(0.9, None))
        dlg.height = dp(460)
        refresh_calendar()
        dlg.open()

    def add_student(self):
        i = self.ids
        user = (i.stu_user.text or "").strip()
        reg = (i.stu_reg.text or "").strip()
        contact = (i.stu_contact.text or "").strip()
        dob = (i.stu_dob.text or "").strip()
        if not all([user, reg, contact, dob]):
            simple_dialog("Error", "All student fields are mandatory"); return
        dt = parse_date_flexible(dob)
        if not dt:
            simple_dialog("Error", "DOB must be DD-MM-YY or recognizable"); return
        # store as dd-mm-yy
        dob_s = fmt_ddmmyy(dt)
        data = load_data()
        if any(user.lower() == u.lower() for u in data.get("students", {})):
            simple_dialog("Error", "Student username already exists"); return
        data.setdefault("students", {})[user] = {
            "reg": reg, "contact": contact, "dob": dob_s, "teacher": self.current_teacher,
            "password": DEFAULT_PASSWORD, "homework": {}, "blocked": False
        }
        save_data(data)
        simple_dialog("Success", f"Student '{user}' added with default password '{DEFAULT_PASSWORD}'")
        for idn in ("stu_user","stu_reg","stu_contact","stu_dob"):
            self.ids[idn].text = ""
        # refresh immediately to show the new student
        self.populate_students_grid()

    def populate_students_grid(self, filter_teacher=None, filter_text=""):
        """
        Populate student cards. Each card now supports:
         - View (inline detail panel)
         - Edit (inline: replace labels with editable fields inside the card)
         - Block/Unblock
         - Delete (requires typing DELETE in a confirm dialog)
        """
        grid = self.ids.students_grid
        grid.clear_widgets()
        data = load_data()
        items = list(data.get("students", {}).items())
        teacher_key = None
        if filter_teacher is not None:
            teacher_key = (filter_teacher or "").strip()
        elif self.current_teacher:
            teacher_key = str(self.current_teacher).strip()
        if teacher_key:
            items = [
                (k, v) for k, v in items
                if str(v.get("teacher", "")).strip().lower() == teacher_key.lower()
            ]
        else:
            items = []
        f = (filter_text or "").strip().lower()
        if f:
            items = [(k,v) for k,v in items if f in k.lower() or f in v.get("reg","").lower() or f in v.get("dob","").lower()]
        if not items:
            grid.add_widget(MDLabel(text="No students yet", halign="center", theme_text_color="Primary"))
            # clear detail panel
            self.ids.student_detail_panel.clear_widgets()
            return
        for idx, (username, info) in enumerate(items):
            # Each card will contain a sublayout where we can swap view / edit modes.
            card = MDCard(size_hint_y=None, height=dp(160), padding=dp(10), radius=[12])
            card.md_bg_color = colored_palette(idx)
            container = MDBoxLayout(orientation="vertical", spacing=dp(6), padding=dp(6))
            # Header
            header = MDLabel(text=username, bold=True, font_style="Subtitle1", size_hint_y=None, height=dp(28))
            container.add_widget(header)
            # Info area: we'll build a BoxLayout that we can update to show either labels or textfields
            info_area = MDBoxLayout(orientation="vertical", spacing=4)
            lbl_info = MDLabel(text=f"Reg: {info.get('reg','')}\nDOB: {info.get('dob','')}\nContact: {info.get('contact','')}", theme_text_color="Secondary")
            info_area.add_widget(lbl_info)
            container.add_widget(info_area)

            # Buttons row
            btns = MDBoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))

            # View -> shows inline in detail panel (reuse existing)
            btn_view = MDRaisedButton(text="View", on_release=partial(self.view_student_detail_inline, username))
            btns.add_widget(btn_view)

            # Edit -> inline: transform info_area to editable fields inside the card
            def make_edit_mode(username_local, info_area_local, header_local, card_local):
                # Build editable content
                data_local = load_data()
                s_local = data_local.get("students", {}).get(username_local, {})
                # clear existing children
                info_area_local.clear_widgets()
                # Editable fields
                reg_field = MDTextField(text=s_local.get("reg",""), hint_text="Reg", mode="rectangle")
                contact_field = MDTextField(text=s_local.get("contact",""), hint_text="Contact", input_filter="int", mode="rectangle")
                dob_field = MDTextField(text=s_local.get("dob",""), hint_text="DOB (DD-MM-YY)", mode="rectangle")
                # Save/Cancel buttons for inline edit
                row = MDBoxLayout(size_hint_y=None, height=dp(36), spacing=8)
                save_btn = MDRaisedButton(text="Save", size_hint_x=None, width=dp(90))
                cancel_btn = MDFlatButton(text="Cancel", size_hint_x=None, width=dp(90))
                row.add_widget(save_btn); row.add_widget(cancel_btn)
                info_area_local.add_widget(reg_field)
                info_area_local.add_widget(contact_field)
                info_area_local.add_widget(dob_field)
                info_area_local.add_widget(row)

                def do_save(inst):
                    regv = (reg_field.text or "").strip()
                    contactv = (contact_field.text or "").strip()
                    dobv = (dob_field.text or "").strip()
                    if not all([regv, contactv, dobv]):
                        simple_dialog("Error", "All fields are mandatory"); return
                    dt = parse_date_flexible(dobv)
                    if not dt:
                        simple_dialog("Error", "DOB not recognizable"); return
                    data_save = load_data()
                    if username_local not in data_save.get("students", {}):
                        simple_dialog("Error", "Student not found"); return
                    data_save["students"][username_local].update({"reg": regv, "contact": contactv, "dob": fmt_ddmmyy(dt)})
                    save_data(data_save)
                    simple_dialog("Success", f"Student '{username_local}' updated")
                    # Restore non-edit view
                    info_area_local.clear_widgets()
                    info_area_local.add_widget(MDLabel(text=f"Reg: {regv}\nDOB: {fmt_ddmmyy(dt)}\nContact: {contactv}", theme_text_color="Secondary"))
                    # refresh teacher students grid to reflect any change in ordering etc.
                    Clock.schedule_once(lambda dt: self.populate_students_grid(), 0.05)
                def do_cancel(inst):
                    # restore original label view
                    info_area_local.clear_widgets()
                    s_restore = load_data().get("students", {}).get(username_local, {})
                    info_area_local.add_widget(MDLabel(text=f"Reg: {s_restore.get('reg','')}\nDOB: {s_restore.get('dob','')}\nContact: {s_restore.get('contact','')}", theme_text_color="Secondary"))

                save_btn.on_release = do_save
                cancel_btn.on_release = do_cancel

            btn_edit = MDFlatButton(text="Edit", on_release=lambda inst, u=username, ia=info_area, hd=header, cd=card: make_edit_mode(u, ia, hd, cd))
            btns.add_widget(btn_edit)

            # Block / Unblock
            def make_block_toggle(u):
                data_local = load_data()
                s_local = data_local.get("students", {}).get(u)
                if not s_local:
                    simple_dialog("Error", "Student not found"); return
                s_local["blocked"] = not s_local.get("blocked", False)
                save_data(data_local)
                simple_dialog("Updated", f"Student '{u}' {'blocked' if s_local['blocked'] else 'unblocked'}")
                Clock.schedule_once(lambda dt: self.populate_students_grid(), 0.05)
            btn_block = MDFlatButton(text="Block" if not info.get("blocked") else "Unblock", on_release=lambda inst, u=username: make_block_toggle(u))
            btns.add_widget(btn_block)

            # Delete (with typed confirmation)
            def do_confirm_delete(u):
                content = MDBoxLayout(orientation="vertical", spacing=8, padding=8)
                content.add_widget(MDLabel(text=f"Type 'DELETE' to confirm deletion of student '{u}'", size_hint_y=None, height=dp(48)))
                confirm_field = MDTextField(hint_text="Type DELETE here", mode="rectangle")
                content.add_widget(confirm_field)
                dialog = MDDialog(title="Confirm Delete Student", type="custom", content_cls=content, size_hint=(0.9, None), buttons=[])
                def do_delete(inst):
                    if (confirm_field.text or "").strip().upper() != "DELETE":
                        simple_dialog("Error", "You must type DELETE to confirm"); return
                    data = load_data()
                    data["students"].pop(u, None)
                    save_data(data)
                    dialog.dismiss()
                    simple_dialog("Deleted", f"Student '{u}' deleted")
                    self.populate_students_grid()
                    self.ids.student_detail_panel.clear_widgets()
                dialog.buttons = [
                    MDFlatButton(text="Cancel", on_release=lambda inst: dialog.dismiss()),
                    MDFlatButton(text="Delete", on_release=do_delete)
                ]
                dialog.open()
            btn_delete = MDFlatButton(text="Delete", on_release=lambda inst, u=username: do_confirm_delete(u))
            btns.add_widget(btn_delete)

            container.add_widget(btns)
            card.add_widget(container)
            grid.add_widget(card)

    def view_students(self, *args):
        if not self.current_teacher:
            simple_dialog("Error", "Teacher is not logged in correctly. Please log out and log in again.")
            return
        data = load_data()
        students = [
            (k, v) for k, v in data.get("students", {}).items()
            if str(v.get("teacher", "")).strip().lower() == str(self.current_teacher).strip().lower()
        ]
        if not students:
            simple_dialog("No students found", f"No students are assigned to teacher '{self.current_teacher}'.\nUse Add Student to create one.")
            self.ids.students_grid.clear_widgets()
            self.ids.student_detail_panel.clear_widgets()
            return
        self.populate_students_grid(filter_teacher=self.current_teacher)

    def filter_students(self, text):
        self.populate_students_grid(filter_text=text)

    def view_student_detail_inline(self, username, *args):
        # Show student details within the teacher screen in the student_detail_panel
        data = load_data()
        s = data.get("students", {}).get(username)
        panel = self.ids.get("student_detail_panel")
        panel.clear_widgets()
        if not s:
            panel.add_widget(MDLabel(text="Student not found", halign="left"))
            return
        header = MDLabel(text=f"Details: {username}", halign="left", size_hint_y=None, height=dp(26), font_style="Subtitle1")
        panel.add_widget(header)
        panel.add_widget(MDLabel(text=f"Reg: {s.get('reg','')}", halign="left", size_hint_y=None, height=dp(22)))
        panel.add_widget(MDLabel(text=f"DOB: {s.get('dob','')}", halign="left", size_hint_y=None, height=dp(22)))
        panel.add_widget(MDLabel(text=f"Contact: {s.get('contact','')}", halign="left", size_hint_y=None, height=dp(22)))
        # Edit inline button that opens the edit fields inside the card via populate_students_grid's edit
        btns = MDBoxLayout(size_hint_y=None, height=dp(36), spacing=8)
        btns.add_widget(MDRaisedButton(text="Edit (inline)", on_release=lambda inst: self._scroll_to_and_edit(username)))
        btns.add_widget(MDFlatButton(text="Clear", on_release=lambda inst: panel.clear_widgets()))
        # Also show Homework for that student with edit/delete actions (subject to date rules)
        btns.add_widget(MDRaisedButton(text="Homework", on_release=partial(self.show_student_homework_with_actions, username)))
        panel.add_widget(btns)

    def _scroll_to_and_edit(self, username):
        # Rough helper: repopulate grid and the teacher can click Edit — this is a small UX helper
        # We'll repopulate students so the inline edit button becomes available visually.
        self.populate_students_grid()
        simple_dialog("Hint", f"Find student '{username}' in list and press Edit to edit inline.")

    def edit_student(self, username, *args):
        # kept for compatibility; we now prefer inline edits in the card itself
        # fallback to the old dialog edit (if user calls this)
        data = load_data()
        s = data.get("students", {}).get(username)
        if not s:
            simple_dialog("Error", "Student not found"); return
        content = MDBoxLayout(orientation="vertical", spacing=8, padding=8)
        reg = MDTextField(text=s.get("reg",""), hint_text="Reg", mode="rectangle")
        contact = MDTextField(text=s.get("contact",""), hint_text="Contact", input_filter="int", mode="rectangle")
        dob = MDTextField(text=s.get("dob",""), hint_text="DOB (DD-MM-YY)", mode="rectangle")
        content.add_widget(reg); content.add_widget(contact); content.add_widget(dob)

        dialog = MDDialog(title=f"Edit Student: {username}", type="custom", content_cls=content, buttons=[])
        dialog.buttons = [
            MDFlatButton(text="Cancel", on_release=lambda inst: dialog.dismiss()),
            MDFlatButton(text="Save", on_release=lambda inst: self._save_student_edit(username, reg.text, contact.text, dob.text, dialog))
        ]
        dialog.open()

    def _save_student_edit(self, username, reg, contact, dob, dialog):
        if not all([username, reg, contact, dob]):
            simple_dialog("Error", "All fields are mandatory"); return
        dt = parse_date_flexible(dob)
        if not dt:
            simple_dialog("Error", "DOB not recognizable"); return
        data = load_data()
        if username not in data.get("students", {}):
            simple_dialog("Error", "Student not found"); dialog.dismiss(); return
        s = data["students"][username]
        s.update({"reg": reg, "contact": contact, "dob": fmt_ddmmyy(dt)})
        save_data(data)
        dialog.dismiss()
        simple_dialog("Success", f"Student '{username}' updated")
        self.populate_students_grid()
        # refresh inline detail panel if visible
        panel = self.ids.get("student_detail_panel")
        if panel and panel.children:
            if any(hasattr(c, "text") and username in getattr(c, "text", "") for c in panel.children):
                self.view_student_detail_inline(username)

    def toggle_block_student(self, username, *args):
        data = load_data()
        stu = data.get("students", {}).get(username)
        if not stu:
            simple_dialog("Error", "Student not found"); return
        stu["blocked"] = not stu.get("blocked", False)
        save_data(data)
        simple_dialog("Updated", f"Student '{username}' {'blocked' if stu['blocked'] else 'unblocked'}")
        self.populate_students_grid()

    def confirm_delete_student(self, username, *args):
        # require typing DELETE
        content = MDBoxLayout(orientation="vertical", spacing=8, padding=8)
        content.add_widget(MDLabel(text=f"Type 'DELETE' to confirm deletion of student '{username}'", size_hint_y=None, height=dp(48)))
        confirm_field = MDTextField(hint_text="Type DELETE here", mode="rectangle")
        content.add_widget(confirm_field)
        dialog = MDDialog(title="Confirm Delete Student", type="custom", content_cls=content, size_hint=(0.9, None), buttons=[])
        def do_delete(inst):
            if (confirm_field.text or "").strip().upper() != "DELETE":
                simple_dialog("Error", "You must type DELETE to confirm"); return
            data = load_data()
            data["students"].pop(username, None)
            save_data(data)
            dialog.dismiss()
            simple_dialog("Deleted", f"Student '{username}' deleted")
            self.populate_students_grid()
            self.ids.student_detail_panel.clear_widgets()
        dialog.buttons = [
            MDFlatButton(text="Cancel", on_release=lambda inst: dialog.dismiss()),
            MDFlatButton(text="Delete", on_release=do_delete)
        ]
        dialog.open()

    def change_teacher_password(self):
        content = MDBoxLayout(orientation="vertical", spacing=8, padding=12, size_hint_y=None, height=dp(220))
        newp = MDTextField(hint_text="New Teacher Password", password=True)
        confirm = MDTextField(hint_text="Confirm New Password", password=True)
        info = MDLabel(text="Fill both fields and press Change", theme_text_color="Secondary", size_hint_y=None, height=dp(24))
        content.add_widget(newp)
        content.add_widget(confirm)
        content.add_widget(info)
        dialog = MDDialog(title="Change Teacher Password", type="custom", content_cls=content, size_hint=(0.9, None))
        def do_change(*args):
            npw = (newp.text or "")
            cpw = (confirm.text or "")
            if not npw:
                simple_dialog("Error", "Password cannot be empty")
                return
            if npw != cpw:
                simple_dialog("Error", "Passwords do not match")
                return
            data = load_data()
            if not self.current_teacher or self.current_teacher not in data.get("teachers", {}):
                simple_dialog("Error", "No teacher logged in")
                return
            data["teachers"][self.current_teacher]["password"] = npw
            save_data(data)
            dialog.dismiss()
            simple_dialog("Success", "Teacher password changed")
        confirm.bind(on_text_validate=do_change)
        # add in-dialog full-width Change button for mobile
        content.add_widget(MDRaisedButton(text="Change", on_release=do_change, size_hint_y=None, height=dp(44)))
        dialog.buttons = [MDFlatButton(text="Cancel", on_release=lambda inst: dialog.dismiss())]
        dialog.open()

    # Photo attach / camera helpers
    _pending_photo = None

    def attach_or_take_photo(self):
        # Present a clearly-visible custom dialog with stacked action buttons
        content = MDBoxLayout(orientation="vertical", spacing=8, padding=12, size_hint_y=None)
        # Ensure height grows to fit buttons
        content.height = dp(160)

        def _choose_file(inst):
            dialog.dismiss()
            self.attach_photo()

        def _use_camera(inst):
            dialog.dismiss()
            self.take_photo()

        btn_file = MDRaisedButton(text="Choose File", md_bg_color=(0.3,0.7,0.95,1), size_hint_y=None, height=dp(44), on_release=_choose_file)
        btn_camera = MDRaisedButton(text="Use Camera", md_bg_color=(0.7,0.6,0.95,1), size_hint_y=None, height=dp(44), on_release=_use_camera)
        btn_cancel = MDFlatButton(text="Cancel", on_release=lambda inst: dialog.dismiss())

        content.add_widget(btn_file)
        content.add_widget(btn_camera)
        content.add_widget(btn_cancel)

        dialog = MDDialog(title="Attach or Take Photo", type="custom", content_cls=content, size_hint=(0.9, None))
        dialog.open()

    def attach_photo(self):
        try:
            from plyer import filechooser
        except Exception:
            simple_dialog("Unavailable", "File chooser not available on this platform")
            return
        def _on_selection(selection):
            if not selection:
                return
            p = selection[0]
            self._pending_photo = p
            lbl = self.ids.get("hw_photo_label")
            if lbl:
                lbl.text = f"Attached: {os.path.basename(p)}"
            simple_dialog("Photo Selected", f"{os.path.basename(p)} attached to next homework")
        try:
            filechooser.open_file(on_selection=_on_selection)
        except TypeError:
            # some plyer versions return list immediately
            sel = filechooser.open_file()
            if sel:
                _on_selection(sel)

    def take_photo(self):
        # Show a live OpenCV preview on desktop and let user press Take
        photos_dir = os.path.join(os.path.dirname(__file__), "photos")
        os.makedirs(photos_dir, exist_ok=True)
        filename = os.path.join(photos_dir, f"hw_{int(datetime.now().timestamp())}.jpg")

        def _set_pending(path):
            if not path:
                simple_dialog("Error", "No photo taken")
                return
            self._pending_photo = path
            lbl = self.ids.get("hw_photo_label")
            if lbl:
                lbl.text = f"Attached: {os.path.basename(path)}"
            simple_dialog("Photo Attached", f"{os.path.basename(path)} attached to next homework")

        # Prefer plyer.camera on non-Windows (mobile) platforms
        if not (os.name == 'nt'):
            try:
                from plyer import camera
                try:
                    camera.take_picture(filename, _set_pending)
                    return
                except Exception:
                    try:
                        res = camera.take_picture(filename)
                        if res:
                            _set_pending(res)
                            return
                    except Exception:
                        pass
            except Exception:
                pass

        # OpenCV preview for desktop
        try:
            import cv2
        except Exception:
            simple_dialog("Unavailable", "Camera not available (plyer and OpenCV not present)")
            return

        from kivy.uix.image import Image as KivyImage
        from kivy.graphics.texture import Texture
        from kivy.clock import Clock
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.button import MDRaisedButton, MDFlatButton

        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW if hasattr(cv2, 'CAP_DSHOW') else 0)
        if not cap.isOpened():
            simple_dialog("Error", "Could not open webcam")
            return

        preview = KivyImage(size_hint_y=None, height=dp(360), allow_stretch=True)
        content = MDBoxLayout(orientation='vertical', spacing=8, padding=8)
        content.add_widget(preview)

        btns = MDBoxLayout(size_hint_y=None, height=dp(48), spacing=8)
        capture_btn = MDRaisedButton(text='Take', md_bg_color=(0.2,0.6,0.86,1))
        cancel_btn = MDFlatButton(text='Cancel')
        btns.add_widget(capture_btn)
        btns.add_widget(cancel_btn)
        content.add_widget(btns)

        dialog = MDDialog(title='Camera Preview', type='custom', content_cls=content, size_hint=(0.95, None))

        frame_holder = {'frame': None}

        def update_frame(dt):
            try:
                ret, frame = cap.read()
                if not ret:
                    return
                frame_holder['frame'] = frame
                h, w = frame.shape[:2]
                buf = frame.tobytes()
                tex = Texture.create(size=(w, h), colorfmt='bgr')
                tex.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
                tex.flip_vertical()
                preview.texture = tex
            except Exception:
                pass

        def stop_preview():
            try:
                Clock.unschedule(update_frame)
            except Exception:
                pass
            try:
                cap.release()
            except Exception:
                pass

        def do_capture(inst):
            frm = frame_holder.get('frame')
            stop_preview()
            if frm is None:
                simple_dialog('Error', 'No frame captured')
                dialog.dismiss()
                return
            try:
                cv2.imwrite(filename, frm)
                _set_pending(filename)
            except Exception as e:
                simple_dialog('Error', f'Failed to save photo: {e}')
            dialog.dismiss()

        def do_cancel(inst):
            stop_preview()
            dialog.dismiss()

        capture_btn.bind(on_release=do_capture)
        cancel_btn.bind(on_release=do_cancel)

        Clock.schedule_interval(update_frame, 1.0 / 20.0)
        dialog.open()

    def _view_photo(self, path):
        if not path or not os.path.exists(path):
            simple_dialog("Error", "Photo not found")
            return
        # Try to load texture directly (more reliable); fall back to AsyncImage
        from kivy.uix.image import AsyncImage as KivyAsyncImage
        try:
            from kivy.core.image import Image as CoreImage
            core = CoreImage(path)
            tex = core.texture
            print('DEBUG: loaded texture size', getattr(tex, 'size', None))
            sys.stdout.flush()
            img = Image(texture=tex, allow_stretch=True)
        except Exception as e:
            print('DEBUG: CoreImage failed:', e)
            sys.stdout.flush()
            img = KivyAsyncImage(source=path, allow_stretch=True)
        dlg = MDDialog(title="Attached Photo", type="custom", content_cls=img, size_hint=(0.95, 0.85))
        dlg.buttons = [MDFlatButton(text="Close", on_release=lambda inst: dlg.dismiss())]
        try:
            dlg.open()
        except Exception as e:
            print("DEBUG: dialog open failed, falling back to OS viewer:", e)
            sys.stdout.flush()
            try:
                if os.name == 'nt':
                    os.startfile(path)
                else:
                    import subprocess
                    if sys.platform == 'darwin':
                        subprocess.run(['open', path])
                    else:
                        subprocess.run(['xdg-open', path])
            except Exception as e2:
                print('DEBUG: fallback open also failed:', e2)
                sys.stdout.flush()
                simple_dialog('Error', 'Unable to display photo')

    def add_homework(self):
        date_s = (self.ids.hw_date.text or "").strip()
        submit_s = (self.ids.hw_submit.text or "").strip()
        details = (self.ids.hw_details.text or "").strip()
        if not all([date_s, submit_s, details]):
            simple_dialog("Error", "All homework fields mandatory"); return
        d_dt = parse_date_flexible(date_s)
        s_dt = parse_date_flexible(submit_s)
        if not d_dt or not s_dt:
            simple_dialog("Error", "Dates must be DD-MM-YY or recognizable"); return
        date = fmt_ddmmyy(d_dt); submit = fmt_ddmmyy(s_dt)
        data = load_data()
        targets = [s for s, si in data.get("students", {}).items() if si.get("teacher") == self.current_teacher]
        for s in targets:
            hw_meta = {"hw_date": date, "submit_date": submit, "done": False}
            if getattr(self, "_pending_photo", None):
                hw_meta["photo"] = self._pending_photo
            data["students"].setdefault(s, {}).setdefault("homework", {})[details] = hw_meta
        save_data(data)
        simple_dialog("Success", f"Homework added for {len(targets)} students")
        self.ids.hw_date.text = ""; self.ids.hw_submit.text = ""; self.ids.hw_details.text = ""
        # clear pending photo after sending
        if getattr(self, "_pending_photo", None):
            self._pending_photo = None
            lbl = self.ids.get("hw_photo_label")
            if lbl:
                lbl.text = "No photo attached"
        self.populate_students_grid()

    def show_student_homework(self, username, *args):
        # older function: show homework read-only
        data = load_data()
        s = data.get("students", {}).get(username, {})
        hw = s.get("homework", {})
        if not hw:
            simple_dialog("No homework", "No homework found for this student"); return
        def parse_date(x):
            dt = parse_date_flexible(x)
            return dt or datetime.max
        items = sorted(hw.items(), key=lambda it: parse_date(it[1].get("submit_date","")))
        content = MDBoxLayout(orientation="vertical", spacing=8, padding=8)
        for title, meta in items:
            txt = f"[b]{title}[/b]\nAssigned: {meta.get('hw_date')}  Due: {meta.get('submit_date')}\nDone: {'Yes' if meta.get('done') else 'No'}"
            if meta.get('photo'):
                txt += f"\nPhoto: {os.path.basename(meta.get('photo'))}"
            tlabel = MDLabel(text=txt, markup=True, size_hint_y=None)
            tlabel.height = dp(96)
            content.add_widget(tlabel)
        dialog = MDDialog(title=f"Homework for {username}", type="custom", content_cls=content, size_hint=(0.95, 0.8), buttons=[])
        dialog.buttons = [MDFlatButton(text="Close", on_release=lambda inst: dialog.dismiss())]
        dialog.open()

    def show_student_homework_with_actions(self, username, *args):
        """
        Show student's homework with action buttons (Edit/Delete) where allowed.
        Edit/Delete allowed only if submit_date is today or future.
        """
        data = load_data()
        s = data.get("students", {}).get(username, {})
        hw = s.get("homework", {})
        if not hw:
            simple_dialog("No homework", "No homework found for this student"); return

        def parse_date_to_dt(x):
            return parse_date_flexible(x) or datetime.max

        items = sorted(hw.items(), key=lambda it: parse_date_to_dt(it[1].get("submit_date","")))
        content = MDBoxLayout(orientation="vertical", spacing=8, padding=8)
        for title, meta in items:
            block = MDBoxLayout(orientation="vertical", spacing=4)
            txt = f"[b]{title}[/b]\nAssigned: {meta.get('hw_date')}  Due: {meta.get('submit_date')}\nDone: {'Yes' if meta.get('done') else 'No'}"
            header = MDLabel(text=txt, markup=True, size_hint_y=None)
            header.height = dp(64)
            block.add_widget(header)
            if meta.get('photo'):
                btn_view_photo = MDFlatButton(text="View Photo", size_hint_x=None, width=dp(120))
                btn_view_photo.on_release = lambda inst, p=meta.get('photo'): self._view_photo(p)
                block.add_widget(btn_view_photo)
            # Only allow edit/delete if submit date is today or future
            allowed = is_today_or_future(meta.get("submit_date",""))
            if allowed:
                actions = MDBoxLayout(size_hint_y=None, height=dp(36), spacing=8)
                btn_edit = MDRaisedButton(text="Edit", size_hint_x=None, width=dp(90))
                btn_delete = MDFlatButton(text="Delete", size_hint_x=None, width=dp(90))
                actions.add_widget(btn_edit)
                actions.add_widget(btn_delete)
                block.add_widget(actions)

                # Edit action: open an inline edit dialog (custom small dialog)
                def do_edit(u=username, t=title, m=meta):
                    content_e = MDBoxLayout(orientation="vertical", spacing=8, padding=8)
                    hw_date_field = MDTextField(text=m.get("hw_date",""), hint_text="Assigned Date (DD-MM-YY)", mode="rectangle")
                    submit_field = MDTextField(text=m.get("submit_date",""), hint_text="Submit Date (DD-MM-YY)", mode="rectangle")
                    done_field = MDTextField(text="Yes" if m.get("done") else "No", hint_text="Done (Yes/No)", mode="rectangle")
                    content_e.add_widget(hw_date_field); content_e.add_widget(submit_field); content_e.add_widget(done_field)
                    dlg = MDDialog(title=f"Edit Homework: {t}", type="custom", content_cls=content_e, size_hint=(0.9, None))
                    def save_edit(inst):
                        hw_d = hw_date_field.text or ""
                        sub_d = submit_field.text or ""
                        done_t = (done_field.text or "").strip().lower() in ("yes","true","1")
                        if not all([hw_d, sub_d]):
                            simple_dialog("Error", "Dates cannot be empty"); return
                        if not parse_date_flexible(hw_d) or not parse_date_flexible(sub_d):
                            simple_dialog("Error", "Dates not recognizable"); return
                        # only allow edits if submit is today or future
                        if not is_today_or_future(sub_d):
                            simple_dialog("Error", "Cannot edit past homework"); return
                        data_save = load_data()
                        if u in data_save.get("students", {}) and t in data_save["students"][u].get("homework", {}):
                            data_save["students"][u].pop(t, None)
                            # we will insert potentially new title if user changed it? For simplicity, keep title same.
                            data_save["students"][u].setdefault("homework", {})[t] = {"hw_date": fmt_ddmmyy(parse_date_flexible(hw_d)), "submit_date": fmt_ddmmyy(parse_date_flexible(sub_d)), "done": done_t}
                            save_data(data_save)
                            dlg.dismiss()
                            simple_dialog("Success", "Homework updated")
                            # reopen the dialog showing actions to reflect changes
                            Clock.schedule_once(lambda dt: self.show_student_homework_with_actions(u), 0.05)
                        else:
                            simple_dialog("Error", "Homework or student not found")
                    dlg.buttons = [MDFlatButton(text="Cancel", on_release=lambda inst: dlg.dismiss()), MDFlatButton(text="Save", on_release=save_edit)]
                    dlg.open()
                btn_edit.on_release = do_edit

                # Delete action: typed confirmation
                def do_delete(u=username, t=title):
                    content_d = MDBoxLayout(orientation="vertical", spacing=8, padding=8)
                    content_d.add_widget(MDLabel(text=f"Type 'DELETE' to delete homework:\n{t}", size_hint_y=None, height=dp(48)))
                    confirm = MDTextField(hint_text="Type DELETE here", mode="rectangle")
                    content_d.add_widget(confirm)
                    dlg = MDDialog(title="Confirm Delete Homework", type="custom", content_cls=content_d, size_hint=(0.9, None))
                    def do_final_delete(inst):
                        if (confirm.text or "").strip().upper() != "DELETE":
                            simple_dialog("Error", "Type DELETE to confirm"); return
                        data_del = load_data()
                        if u in data_del.get("students", {}) and t in data_del["students"][u].get("homework", {}):
                            # only allow delete if homework due date is today or future
                            if not is_today_or_future(data_del["students"][u]["homework"][t].get("submit_date","")):
                                simple_dialog("Error", "Cannot delete past homework"); return
                            data_del["students"][u]["homework"].pop(t, None)
                            save_data(data_del)
                            dlg.dismiss()
                            simple_dialog("Deleted", f"Homework '{t}' deleted")
                            Clock.schedule_once(lambda dt: self.show_student_homework_with_actions(u), 0.05)
                        else:
                            simple_dialog("Error", "Homework not found")
                    dlg.buttons = [MDFlatButton(text="Cancel", on_release=lambda inst: dlg.dismiss()), MDFlatButton(text="Delete", on_release=do_final_delete)]
                    dlg.open()
                btn_delete.on_release = lambda inst, u=username, t=title: do_delete(u,t)

            else:
                # Past homework - read-only label showing it's locked
                block.add_widget(MDLabel(text="[i]This homework is past due and locked (read-only).[/i]", markup=True, size_hint_y=None, height=dp(24)))
            content.add_widget(block)
        dialog = MDDialog(title=f"Homework for {username}", type="custom", content_cls=content, size_hint=(0.95, 0.8), buttons=[])
        dialog.buttons = [MDFlatButton(text="Close", on_release=lambda inst: dialog.dismiss())]
        dialog.open()

    def show_student_homework(self, username, *args):
        # keep compatibility with older call; delegate to action-capable view
        self.show_student_homework_with_actions(username)

# ---------- Student ----------
class StudentScreen(Screen):
    current_student = None
    _hw_cache = []

    def on_enter(self, *args):
        # Hide username field if logged in and show welcome & date
        if self.current_student:
            self.ids.student_user_field.disabled = True
            self.ids.student_user_field.opacity = 0
        else:
            self.ids.student_user_field.disabled = False
            self.ids.student_user_field.opacity = 1
        self.update_welcome()
        self.update_datetime_label()

    def update_datetime_label(self, *l):
        lbl = self.ids.get("dt_student")
        if lbl:
            lbl.text = datetime.now().strftime("%d-%m-%y %H:%M:%S")
        Clock.schedule_once(self.update_datetime_label, 1)

    def update_welcome(self):
        user = self.current_student or (self.ids.student_user_field.text or "").strip()
        if not user:
            self.ids.student_welcome.text = ""
            return
        data = load_data()
        s = data.get("students", {}).get(user)
        if not s:
            self.ids.student_welcome.text = ""
            return
        teacher = s.get("teacher")
        teacher_info = ""
        if teacher:
            t = data.get("teachers", {}).get(teacher, {})
            teacher_info = f" | Teacher: {teacher} ({t.get('grade','')}/{t.get('section','')})"
        self.ids.student_welcome.text = f"Welcome, {user}{teacher_info}"

    def load_and_show_homework(self):
        user = (self.ids.student_user_field.text or "").strip() or self.current_student
        if not user:
            simple_dialog("Error", "Provide student username or login as student"); return
        data = load_data()
        s = data.get("students", {}).get(user)
        if not s:
            simple_dialog("Error", "Student not found"); return
        if s.get("blocked"):
            simple_dialog("Blocked", "Student account is blocked"); return
        hw = s.get("homework", {})
        grid = self.ids.student_hw_grid
        grid.clear_widgets()
        if not hw:
            grid.add_widget(MDLabel(text="No homework assigned", halign="center", theme_text_color="Primary"))
            self._hw_cache = []
            return
        def parse_date(x):
            dt = parse_date_flexible(x)
            return dt or datetime.max
        items = sorted(hw.items(), key=lambda it: parse_date(it[1].get("submit_date","")))
        self._hw_cache = items
        for idx, (title, meta) in enumerate(items):
            card = MDCard(size_hint_y=None, height=dp(140), padding=dp(10), radius=[12])
            card.md_bg_color = colored_palette(idx)
            box = MDBoxLayout(orientation="vertical", spacing=dp(6), padding=dp(6))
            box.add_widget(MDLabel(text=title, bold=True, font_style="Subtitle1", size_hint_y=None, height=dp(28)))
            box.add_widget(MDLabel(text=f"Assigned: {meta.get('hw_date','')}\nDue: {meta.get('submit_date','')}\nDone: {'Yes' if meta.get('done') else 'No'}", theme_text_color="Secondary"))

            # If a photo was attached, show a View Photo button (always visible)
            photo_path = meta.get("photo")
            if photo_path:
                def _open_photo(p=photo_path):
                    # Resolve relative paths
                    pth = p
                    if not os.path.exists(pth):
                        pth = os.path.join(os.path.dirname(__file__), p)
                    self.student_view_photo(pth)
                view_btn = MDRaisedButton(text="View Photo", size_hint=(None, None), size=(dp(120), dp(36)), on_release=lambda inst, fn=_open_photo: fn())
                box.add_widget(view_btn)
            card.add_widget(box)
            grid.add_widget(card)

    def mark_done(self, user, title, *args):
        data = load_data()
        if user in data.get("students", {}) and title in data["students"][user].get("homework", {}):
            data["students"][user]["homework"][title]["done"] = True
            save_data(data)
            simple_dialog("Success", f"Marked '{title}' as done")
            self.load_and_show_homework()
        else:
            simple_dialog("Error", "Homework not found")

    def filter_student_homework(self, text):
        txt = (text or "").strip().lower()
        grid = self.ids.student_hw_grid
        grid.clear_widgets()
        if not self._hw_cache:
            self.load_and_show_homework()
            return
        items = [it for it in self._hw_cache if txt in it[0].lower() or txt in (it[1].get("hw_date","") or "").lower() or txt in (it[1].get("submit_date","") or "").lower()]
        if not items:
            grid.add_widget(MDLabel(text="No homework matches", halign="center", theme_text_color="Primary"))
            return
        for idx, (title, meta) in enumerate(items):
            card = MDCard(size_hint_y=None, height=dp(140), padding=dp(10), radius=[12])
            card.md_bg_color = colored_palette(idx)
            box = MDBoxLayout(orientation="vertical", spacing=dp(6), padding=dp(6))
            box.add_widget(MDLabel(text=title, bold=True, font_style="Subtitle1", size_hint_y=None, height=dp(28)))
            box.add_widget(MDLabel(text=f"Assigned: {meta.get('hw_date','')}\nDue: {meta.get('submit_date','')}\nDone: {'Yes' if meta.get('done') else 'No'}", theme_text_color="Secondary"))
            card.add_widget(box); grid.add_widget(card)

    def student_view_photo(self, path, *args):
        print("DEBUG: student_view_photo called with:", path)
        sys.stdout.flush()
        if not path or not os.path.exists(path):
            alt = os.path.join(os.path.dirname(__file__), path) if path else None
            print("DEBUG: exists:", os.path.exists(path) if path else None, "alt_exists:", os.path.exists(alt) if alt else None)
            sys.stdout.flush()
            simple_dialog("Error", "Photo not found")
            return
        # Use a sized container and assign texture explicitly to avoid black rendering
        from kivy.uix.image import AsyncImage as KivyAsyncImage
        content = MDBoxLayout(orientation='vertical', padding=8, spacing=8)
        try:
            from kivy.core.image import Image as CoreImage
            # Prefer converting via Pillow to a standard RGBA PNG first (fixes many backend issues)
            try:
                from PIL import Image as PILImage
                pil = PILImage.open(path).convert('RGBA')
                tmp_fn = os.path.join(os.path.dirname(__file__), 'photos', f'tmp_view_{int(datetime.now().timestamp()*1000)}.png')
                pil.save(tmp_fn)
                core = CoreImage(tmp_fn)
            except Exception:
                core = CoreImage(path)
            tex = core.texture
            print('DEBUG: loaded texture size', getattr(tex, 'size', None))
            sys.stdout.flush()
            img = Image(allow_stretch=True, size_hint_y=None, height=dp(360))
            img.texture = tex
        except Exception as e:
            print('DEBUG: CoreImage failed:', e)
            sys.stdout.flush()
            img = KivyAsyncImage(source=path, allow_stretch=True, size_hint_y=None, height=dp(360))
        content.add_widget(img)
        dlg = MDDialog(title='Attached Photo', type='custom', content_cls=content, size_hint=(0.95, None))
        dlg.height = dp(440)
        try:
            dlg.open()
        except Exception as e:
            print('DEBUG: dialog open failed, falling back to OS viewer:', e)
            sys.stdout.flush()
            try:
                if os.name == 'nt':
                    os.startfile(path)
                else:
                    import subprocess
                    if sys.platform == 'darwin':
                        subprocess.run(['open', path])
                    else:
                        subprocess.run(['xdg-open', path])
            except Exception as e2:
                print('DEBUG: fallback open also failed:', e2)
                sys.stdout.flush()
                simple_dialog('Error', 'Unable to display photo')

    def change_student_password(self):
        content = MDBoxLayout(orientation="vertical", spacing=8, padding=12, size_hint_y=None, height=dp(220))
        newp = MDTextField(hint_text="New Student Password", password=True)
        confirm = MDTextField(hint_text="Confirm New Password", password=True)
        info = MDLabel(text="Fill both fields and press Change", theme_text_color="Secondary", size_hint_y=None, height=dp(24))
        content.add_widget(newp)
        content.add_widget(confirm)
        content.add_widget(info)
        dialog = MDDialog(title="Change Student Password", type="custom", content_cls=content, size_hint=(0.9, None))
        def do_change(*args):
            npw = (newp.text or "")
            cpw = (confirm.text or "")
            if not npw:
                simple_dialog("Error", "Password cannot be empty")
                return
            if npw != cpw:
                simple_dialog("Error", "Passwords do not match")
                return
            user = self.current_student or (self.ids.student_user_field.text or "").strip()
            if not user:
                simple_dialog("Error", "No student selected")
                return
            data = load_data()
            if user not in data.get("students", {}):
                simple_dialog("Error", "Student not found")
                return
            data["students"][user]["password"] = npw
            save_data(data)
            dialog.dismiss()
            simple_dialog("Success", "Password changed")
        confirm.bind(on_text_validate=do_change)
        content.add_widget(MDRaisedButton(text="Change", on_release=do_change, size_hint_y=None, height=dp(44)))
        dialog.buttons = [MDFlatButton(text="Cancel", on_release=lambda inst: dialog.dismiss())]
        dialog.open()

# ------------------ App ------------------
class HomeworkApp(MDApp):
    def build(self):
        print("DEBUG: HomeworkApp.build() start")
        sys.stdout.flush()
        ensure_data_file()
        print("DEBUG: ensure_data_file() completed")
        sys.stdout.flush()
        self.title = "Homework Manager (Pastel)"
        try:
            # slightly stronger theme contrast without changing layout
            self.theme_cls.primary_palette = "BlueGray"
            self.theme_cls.primary_hue = "700"
            self.theme_cls.accent_palette = "Pink"
            self.theme_cls.accent_hue = "400"
            self.theme_cls.theme_style = "Light"
        except Exception:
            pass
        root = Builder.load_string(KV)
        print("DEBUG: Builder.load_string returned", type(root))
        sys.stdout.flush()
        try:
            from kivy.core.window import Window as _Win
            print("DEBUG: Window size (before):", _Win.size, "position:", getattr(_Win, 'left', 'N/A'), getattr(_Win, 'top', 'N/A'))
            _Win.clearcolor = (1, 1, 1, 1)
            try:
                _Win.show()
            except Exception:
                pass
            try:
                _Win.raise_window()
            except Exception:
                pass
            print("DEBUG: Window size (after):", _Win.size)
            sys.stdout.flush()
        except Exception as e:
            print("DEBUG: Window check failed:", e)
            sys.stdout.flush()
        try:
            from kivy.clock import Clock
            def _started(dt):
                try:
                    print("DEBUG: App started (scheduled). Showing MessageBox")
                    sys.stdout.flush()
                    ctypes.windll.user32.MessageBoxW(0, "HomeworkApp started (Kivy window may be hidden)", "HomeworkApp Debug", 0)
                except Exception:
                    print("DEBUG: MessageBox failed")
                    sys.stdout.flush()

            Clock.schedule_once(_started, 0.5)
        except Exception:
            pass
        return root

if __name__ == "__main__":
    print("DEBUG: Starting HomeworkApp().run()")
    sys.stdout.flush()
    HomeworkApp().run()
    print("DEBUG: HomeworkApp.run() returned")
    sys.stdout.flush()
