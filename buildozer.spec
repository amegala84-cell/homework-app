[app]
title = Homework App
package.name = homeworkapp
package.domain = com.sakshain
source.dir = .
source.include_exts = py,png,jpg,jpeg,json,kv,txt
source.include_patterns = photos/*

version = 1.0.0
requirements = python3,kivy==2.3.0,kivymd==1.2.0,plyer
orientation = portrait
fullscreen = 0

android.permissions = INTERNET,CAMERA,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 35
android.minapi = 26
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 0