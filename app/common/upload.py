from datetime import datetime
import re,os,hashlib
from werkzeug.utils import secure_filename
from PIL import Image
from flask import flash

class Upload:
    def save_image_file(self,static_folder,dir,file,crop=False,extra_large=False):
        if file is None:
            return None
        date = datetime.utcnow()#用于增加随机性
        filename = secure_filename(file.filename)+str(date)
        filename = hashlib.md5(filename.encode()).hexdigest()[8:-8]#16位MD5就是取32位的中间16位
        year_month = '%x%x' % (date.year, date.month)#目录

        #static/20166
        path = os.path.join(static_folder,dir,year_month)
        if not os.path.exists(path):
            os.mkdir(path)

        try:

            image_info = {}
            # static/20166/a89e2f074b7882181.png
            im = Image.open(file)

            # 需要裁剪
            if crop:
                crop_img = self.crop_square(im)
                if crop_img:
                    im = crop_img
                    flash('裁剪后:%d %d' % (im.size[0],im.size[1]))


            #im.size存储的是(width,height)
            image_info['aspect_ratio'] = round(im.size[0]/im.size[1],3)
            image_info['format'] = im.format
            image_info['path'] = os.path.join(dir,year_month,filename)




            #是否需要储存加大图片
            if extra_large:
                im.thumbnail((800,800))
                image_info['size'] = im.size#(width,height)
                im.save(os.path.join(path, filename + '_xl.png'))
                im.thumbnail((400, 550))
                im.save(os.path.join(path, filename + '_l.png'))
                im.thumbnail((200, 280))
                im.save(os.path.join(path, filename + '_m.png'))
                im.thumbnail((125, 150))
                im.save(os.path.join(path, filename + '_s.png'))
            else:
                im.thumbnail((240,240))
                image_info['size'] = im.size
                im.save(os.path.join(path,filename+'_xl.png'))
                im.thumbnail((120,120))
                im.save(os.path.join(path,filename+'_l.png'))
                im.thumbnail((60,60))
                im.save(os.path.join(path,filename+'_m.png'))
                im.thumbnail((30,30))
                im.save(os.path.join(path,filename+'_s.png'))

            image_info['status'] = 1

            return image_info

        except Exception as err:
            image_info = {}
            image_info['status'] = -1
            image_info['error'] = err
            return image_info

    #从中心裁剪出一个正方形
    def crop_square(self,im):
        try:
            #得到变长
            side_lenght = int(im.size[0] if im.size[0]<im.size[1] else im.size[1])
            x = int(im.size[0]/2-side_lenght/2)
            y = int(im.size[1]/2-side_lenght/2)
            region = (x, y, x+side_lenght, y+side_lenght)
            flash(region)
            return im.crop(region)
        except Exception as err:
            flash('裁剪图片出错')
            return None
