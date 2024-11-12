# -*- encoding: utf-8 -*-
"""
Copyright (c) 2024 - present Mahmoud Qzibar
"""

from flask_login import login_required, current_user, login_user, logout_user
from flask import render_template, redirect, request, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy 
from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime
from werkzeug.utils import secure_filename

from apps import db, login_manager
from apps.authentication.forms import LoginForm, CreateAccountForm
from apps.authentication.util import verify_pass
from apps.home import blueprint
from apps.authentication.models import Users

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'apps', 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@blueprint.route('/')
def route_default():
    return redirect(url_for('home_blueprint.login'))

@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm(request.form)
    if 'login' in request.form:
        username = request.form['username']
        password = request.form['password']
        user = Users.query.filter_by(username=username).first()

        if user and verify_pass(password, user.password):
            login_user(user)
            return redirect(url_for('home_blueprint.index'))

        return render_template('accounts/login.html', msg='Wrong user or password', form=login_form)

    if not current_user.is_authenticated:
        return render_template('accounts/login.html', form=login_form)
    return redirect(url_for('home_blueprint.index'))

@blueprint.route('/register', methods=['GET', 'POST'])
def register():
    create_account_form = CreateAccountForm(request.form)
    if 'register' in request.form:
        username = request.form['username']
        email = request.form['email']

        user = Users.query.filter_by(username=username).first()
        if user:
            return render_template('accounts/register.html', msg='Username already registered', form=create_account_form)

        user = Users.query.filter_by(email=email).first()
        if user:
            return render_template('accounts/register.html', msg='Email already registered', form=create_account_form)

        user = Users(**request.form)
        db.session.add(user)
        db.session.commit()
        logout_user()

        return render_template('accounts/register.html', msg='Account created successfully.', success=True, form=create_account_form)
    return render_template('accounts/register.html', form=create_account_form)

@blueprint.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home_blueprint.login'))

@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('home/page-403.html'), 403

@blueprint.errorhandler(403)
def access_forbidden(error):
    return render_template('home/page-403.html'), 403

@blueprint.errorhandler(404)
def not_found_error(error):
    return render_template('home/page-404.html'), 404

@blueprint.errorhandler(500)
def internal_error(error):
    return render_template('home/page-500.html'), 500

class Meme(db.Model):
    __tablename__ = 'memes'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    text = db.Column(db.String(255), nullable=False)
    text_size = db.Column(db.Integer, nullable=False)
    text_color = db.Column(db.String(7), nullable=False)
    text_x = db.Column(db.Integer, nullable=False)
    text_y = db.Column(db.Integer, nullable=False)
    created_by = db.Column(db.Integer, nullable=False)

@blueprint.route('/create_meme', methods=['POST'])
@login_required
def create_meme():
    meme_text = request.form['meme_text']
    text_size = int(request.form['text_size'])
    text_color = request.form['text_color']
    text_x = int(request.form['text_x'])
    text_y = int(request.form['text_y'])
    image_file = request.files['image']

    if image_file and image_file.filename != '':
        filename = secure_filename(f"meme_{datetime.now().strftime('%Y%m%d%H%M%S')}.png")
        save_path = os.path.join(UPLOAD_FOLDER, filename)

        image = Image.open(image_file).convert("RGBA")
        image = image.resize((500, 500))

        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("arial.ttf", text_size)
        except IOError:
            font = ImageFont.load_default()

        draw.text((text_x, text_y), meme_text, font=font, fill=text_color)
        image.save(save_path, "PNG")

        # Save to database
        new_meme = Meme(
            filename=filename,
            text=meme_text,
            text_size=text_size,
            text_color=text_color,
            text_x=text_x,
            text_y=text_y,
            created_by=current_user.id
        )
        db.session.add(new_meme)
        db.session.commit()

        return redirect(url_for('home_blueprint.gallery'))

    flash('Failed to create meme. Please try again.')
    return redirect(url_for('home_blueprint.index'))

@blueprint.route('/gallery')
@login_required
def gallery():
    memes = Meme.query.filter_by(created_by=current_user.id).all()
    return render_template('home/gallery.html', memes=memes)

@blueprint.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename))
