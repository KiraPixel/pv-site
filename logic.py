from flask import redirect, url_for, render_template
import mysqlrequests


class Simplifier:

    @staticmethod
    def redirect_with_notification_text(url, head, text):
        return redirect(url_for(f'.{url}', isNotification=True, NotificationHead=head, NotificationText=text))

    @staticmethod
    def render_with_notification_text(html, head, text):
        return render_template(f"{html}.html", isNotification=True, NotificationHead=head, NotificationText=text)

    @staticmethod
    def render_access_error(html):
        notification_head = "Ошибка доступа [AccessToken ERROR]"
        notification_text = "Упс! Случилось, что-то не очень хорошее... Мы это записали. Но не волнуйтесь, если вы ничего не натворили, то все будет в порядке :)"
        return render_template(f'{html}.html', isNotification=True, NotificationHead=notification_head, NotificationText=notification_text)

    @staticmethod
    def redirect_access_error(url):
        notification_head = "Ошибка доступа [AccessToken ERROR]"
        notification_text = "Упс! Случилось, что-то не очень хорошее... Мы это записали. Но не волнуйтесь, если вы ничего не натворили, то все будет в порядке :)"
        return redirect(url_for(f'.{url}', isNotification=True, NotificationHead=notification_head, NotificationText=notification_text))


def check_registration(user_id):
    user = mysqlrequests.User(user_id)
    if user.check == -1:
        user.first_registration()
        check_registration(user_id)
        return
    if user.check == 0:
        return False
    else:
        return True


def transfer_money(user_id, minecraft_nick, money, type):
    if user_id == "System":
        user_id = 1117271244383977503
    if money <= 0:
        return False
    sender_user = mysqlrequests.User(user_id)

    if sender_user.check != 1:
        return False
    elif sender_user.money < money:
        return False

    getter_user = mysqlrequests.User(minecraft_nick)
    if getter_user.check != 1:
        return False
    sender_user.add_money(money * -1)
    mysqlrequests.TransactionController.add_new_transaction(sender_user.discord_id, money * -1, type,
                                                            getter_user.minecraft_nick)
    getter_user.add_money(money)
    mysqlrequests.TransactionController.add_new_transaction(getter_user.discord_id, money, type,
                                                            sender_user.minecraft_nick)
    return True
