

from threading import Thread
from flask import current_app,render_template
from flask.ext.mail import Message
from . import mail,create_app


def send_async_email(app,msg):
    with app.app_context():
        mail.send(msg)

def send_email(to,subject,template,**kwargs):
    msg = Message(current_app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + subject,
                  sender=current_app.config['FLASKY_MAIL_SENDER'], recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    #with current_app.app_context():
    #    mail.send(msg)
    #current_app只是一个代理获取而已,传递给其它子线程获取到的依然是子线程的上下文
    # 必须_get_current_object线获取到原始对象再传递过去
    app = current_app._get_current_object()
    thr = Thread(target=send_async_email, args=(app, msg))
    thr.start()
    return thr