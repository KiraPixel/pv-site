import os

from flask import Flask, redirect, render_template, url_for, request
from flask_discord import DiscordOAuth2Session, requires_authorization, Unauthorized
from flask_mysqldb import MySQL
import time

import mysqlrequests
from config import site_settings
import logic
from logic import Simplifier


app = Flask(__name__)

app.secret_key = b"asdasdasd asda sd asd"
app.debug = True
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "false"

app.config["DISCORD_CLIENT_ID"] = site_settings['DISCORD_CLIENT_ID']
app.config["DISCORD_CLIENT_SECRET"] = site_settings['DISCORD_CLIENT_SECRET']
app.config["DISCORD_REDIRECT_URI"] = f"http://{site_settings['host']}{site_settings['DISCORD_REDIRECT_URI']}"
app.config["DISCORD_BOT_TOKEN"] = site_settings['DISCORD_BOT_TOKEN']

discord = DiscordOAuth2Session(app)


@app.context_processor
def any_data_processor():
    time.sleep(0.1)
    user = None
    user_db = None
    is_sale_check = False
    is_user_authorized = False
    is_minecraft_check = False
    access_token = None
    if discord.get_authorization_token() is not None:
        access_token = discord.get_authorization_token()['access_token']

    if discord.user_id is not None:
        user = discord.fetch_user()
        user_id = discord.fetch_user().id
        is_user_authorized = True

        if logic.check_registration(user_id):
            is_minecraft_check = True
        else:
            is_minecraft_check = False

        user_db = mysqlrequests.User(user_id)
        user_db.user_update()
        if user_db.saleman == 1:
            is_sale_check = True

    return dict(
        user_authorized=is_user_authorized,
        user=user, user_db=user_db,
        sale_check=is_sale_check,
        minecaft_check=is_minecraft_check,
        AccessToken=access_token,
    )


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(Unauthorized)
def handle_error(e):
    return redirect(url_for('.index', isNotification=True, NotificationHead="Ошибка доступа", NotificationText="Авторизуйтесь на сайте для посещения это страницы") )

# @app.errorhandler(Exception)
# def handle_error(e):
#     return redirect(url_for('.index'))


@app.route("/me/")
def me():
    if not discord.authorized:
        return redirect("/")
    discord_user = discord.fetch_user()
    user_transactions = mysqlrequests.TransactionController.get_all_transaction(discord_user.id)
    return render_template("profile.html", user_transactions=user_transactions)


@app.route("/minecraft/", methods=["GET", "POST"])
def minecraft():
    if not discord.authorized:
        return redirect("/")
    discord_user = discord.fetch_user().id
    user = mysqlrequests.User(discord_user)
    if user.check == 1:
        return redirect(url_for('.index', isNotification=True, NotificationHead="Регистрация", NotificationText="Вы уже подтвердили ваш майнкрафт аккаунт!") )
    if request.method == "POST":
        registration_code = request.form.get("registrationCode")
        try:
            registration_code = int(registration_code)
            if 100000 <= registration_code <= 999999:
                if not user.add_minecraft_info(registration_code):
                    return render_template("minecraft.html", isNotification=True, NotificationHead="Регистрация", NotificationText="Неверный код регистрации!")
                else:
                    return redirect(url_for('.index', isNotification=True, NotificationHead="Регистрация", NotificationText="Вы подтвердили ваш майнкрафт аккаунт!") )

        except ValueError:
            return render_template('404.html'), 404

    return render_template("minecraft.html")


@app.route("/transfer_money/", methods=["GET", "POST"])
def transfer_money():
    is_notification = request.args.get('isNotification')
    notification_head = request.args.get('NotificationHead')
    notification_text = request.args.get('NotificationText')
    access_token = discord.get_authorization_token()['access_token']

    if request.method == "GET":
        return render_template("transfer_money.html", AccessToken=access_token, isNotification=is_notification, NotificationHead=notification_head, NotificationText=notification_text)

    discord_user = discord.fetch_user()
    db_user = mysqlrequests.User(discord.user_id)
    if db_user.check != 1:
        return Simplifier.redirect_with_notification_text('index', "Перевод", "Сначала подтверди свой майнкрафт аккаунт :3")
    minecraft_nick = request.form.get("minecraft-nick")
    money = int(request.form.get("money-amount"))
    post_access_token = request.form.get("access-token")

    if access_token != post_access_token:
        return Simplifier.redirect_access_error('transfer_money')

    if db_user.minecraft_nick == minecraft_nick:
        notification_text = "Вы не можете перевести сами себе... Это ведь странно..."
    elif logic.transfer_money(discord_user.id, minecraft_nick, money, 'Перевод'):
        notification_text = f"Успешный перевод для {minecraft_nick}"
    else:
        notification_text = f"При переводе для {minecraft_nick} произошла ошибка. Проверьте правильность написания ника."

    return redirect(url_for('.transfer_money', isNotification=True, NotificationHead="Перевод", NotificationText=notification_text))


@app.route("/my_shop", methods=["GET", "POST"])
def my_shop():
    context = any_data_processor()
    user = context['user']
    db_user = context['user_db']
    if db_user.check != 1:
        return Simplifier.redirect_with_notification_text('index', "Мой магазин", "Сначала подтверди свой майнкрафт аккаунт :3")
    access_token = discord.get_authorization_token()['access_token']

    if request.method == "GET":
        if db_user.saleman == 1:
            return render_template("myshop.html")
        return render_template("newshop.html")

    post_access_token = request.form.get("access-token")
    if access_token == post_access_token:
        return Simplifier.render_access_error('myshop')

    if request.form.get("newShopName") is not None:
        new_shop_mame = request.form.get("newShopName")
        if db_user.money >= 10:
            logic.transfer_money(user.id, 'System', 10, 'Покупка магазина')
            db_user.set_saleman(1)
            new_shop = mysqlrequests.Shop(owner_id=user.id)
            if not new_shop.create_shop(new_shop_mame):
                logic.transfer_money('System', user.id, 10, 'Возврат')
                return Simplifier.render_with_notification_text('newshop',"Мой магазин", "При создании магазина произошла ошибка")
            return render_template("myshop.html")
        else:
            return Simplifier.render_with_notification_text('newshop', "Мой магазин", "Недостаточно средств")
    elif request.form.get("form1") is not None:
        new_product = {
            'product_name': request.form.get("form1"),
            'product_image': request.form.get("form2"),
            'product_count': request.form.get("form3"),
            'product_price': request.form.get("form4"),
        }
        print(new_product['product_name'])
    else:
        print('пиздец')
    return render_template("myshop.html")



@app.route("/")
@app.route("/home")
def index():
    isNotification = request.args.get('isNotification')
    notificationHead = request.args.get('NotificationHead')
    NotificationText = request.args.get('NotificationText')
    return render_template("index.html", isNotification=isNotification, NotificationHead=notificationHead, NotificationText=NotificationText)


@app.route("/login/")
def login():
    return discord.create_session(modified=True)


@app.route("/logout/")
def logout():
    discord.revoke()
    isNotification = request.args.get('isNotification')
    notificationHead = request.args.get('NotificationHead')
    NotificationText = request.args.get('NotificationText')
    return redirect(url_for('.index', isNotification=isNotification, NotificationHead=notificationHead, NotificationText=NotificationText))


@app.route("/callback/")
def callback():
    discord.callback()
    users = discord.fetch_user()
    return redirect(url_for(".index"))



if __name__ == "__main__":
    app.run(host=site_settings['host'])