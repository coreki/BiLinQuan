

function join_group(url){
    //var url = "{{ url_for('.join_group',id=group.id) }}";
    url += '?verify='+$('#join-verify-answer').get(0).value;
    location.href = url
}

/**
 * 发布新博文相关
 */

//发布新博文的类
function NewPost() {

    //点击插入投票按钮
    this.click_poll_expand = function () {
        var isHide = $('#new-post-poll-expand').css('display') == 'none';
        display_poll_expand(isHide);

    }

    //点击插入图片按钮
    this.click_images_expand = function () {
        var isHide = $('#new-post-images-expand').css('display') == 'none';
        display_images_expand(isHide);

    }

    //显示/隐藏投票
    function display_images_expand(display) {

        //images_count的计数器设为0
        imageFiles.images_count.set(0);

        if (display) {
            $('#new-post-images-expand').css('display', 'block');

        }
        else {
            $('#new-post-images-expand').css('display', 'none');
        }
    }

    //显示/隐藏投票
    function display_poll_expand(display) {
        //options的计数器设为0
        poll.options_count.set(0);

        if (display) {
            $('#new-post-poll-expand').css('display', 'block');

            //清空所有选项
            $('#new-post-poll-options').html("");
            //添加2个选项
            for (var i = 0; i < 2; i++)
                poll.add_new_poll_option();

        }
        else {
            $('#new-post-poll-expand').css('display', 'none');
            //清空所有选项
            $('#new-post-poll-options').html("");
        }
    }

    //检查发布内容
    this.check_new_post = function () {
        var new_post_text = $('#body').get(0).value;
        if (new_post_text.length < 2) {
            alert('发布的内容应至少输入两个字');
            return false;
        }

        if (poll.check_new_post_poll() == false)
            return false;

        return true;

    }




}

//投票类
function Poll() {

    //图片计数器
    this.options_count = {
        get:function(){
            return $('#poll_options_count').val()*1;
        },
        set:function(value){
            $('#poll_options_count').val(value);
        },
        add:function(){
            this.set(this.get()+1);
        },
        sub:function(){
            this.set(this.get()-1);
        }

    };

    //添加投票选项
    this.add_new_poll_option = function () {

        var template = '<input type="text" class="form-control poll-options-input" ' +
                'id="poll-option{option_index}"  name="poll-option{option_index}" ' +
                'placeholder="选项 {show_index}">';
        var domEleCount = $('#poll_options_count').get(0);
        var new_index = domEleCount.value * 1;

        //真是索引是0开始,显示给用户看是1开始
        var input_html = template.format({option_index: new_index, show_index: new_index + 1});

        //修改计数+1
        this.options_count.add();
        //替换HTML,必须用APPEND,用HTML()的话用户输入的值会消失
        $("#new-post-poll-options").append(input_html);

        //alert(html)

    }


    //检查投票参数
    this.check_new_post_poll = function () {
        var options_count = this.options_count.get();
        if (options_count == 0)//没有发起投票
            return true;

        //alert(options_count)

        var check_result_count = 0;
        for (var i = 0; i < options_count; i++) {
            var option_id = '#poll-option' + i;
            var option_text = $(option_id).get(0).value;
            //alert(option_text)
            if (option_text.length >= 2)
                check_result_count++;
        }

        if (check_result_count < 2) {
            alert('投票选项应至少两个');
            return false;
        }

        if (check_result_count > 32) {
            alert('投票选项不能超出32个');
            return false;
        }

        var max_choice = $('#poll_max_choice').get(0).value;
        if (max_choice == "" || max_choice < 1) {
            alert('投票的多选数目应该在1-' + check_result_count);
            return false;
        }

        var expire_days = $('#poll_expire_days').get(0).value;
        if (expire_days == "" || expire_days < 1 || expire_days > 999) {
            alert('投票过期天数应该在1-999天之间');
            return false;
        }

        return true;
    }
}

//定义imageFileList面向对象,和类差不多
function ImageFiles() {

    //保存THIS对象,供私有成员调用
    var that = this;
    //图片计数器
    this.images_count = {
        get:function(){
            return $('#images_count').val()*1;
        },
        set:function(value){
            $('#images_count').val(value);
        },
        add:function(){
            this.set(this.get()+1);
        },
        sub:function(){
            this.set(this.get()-1);
        }

    };

    //添加新图片
    this.add_new_image = function() {

        var count = this.images_count.get();
        //alert("当前file计数:"+count)

        if (count >= 9) {
            alert('最多可选择9账图片');
            return;
        }

        //遍历1-9ID,寻找可用索引
        var index = -1;
        for (var i = 0; i < 9; i++) {
            var file_input = $("input[id=image_file_" + i + "]");
            //不存在
            if (file_input.length == 0) {
                index = i;
                break;
            }//值为空,没有选文件的空闲file input,则直接弹出浏览对话框,
            else if ($(file_input).val() == "") {
                //弹出文件浏览对话框
                file_input.click();
                return;
            }
        }

        if (index == -1) {
            alert('1-9的图片ID已经沾满');
            return;
        }

        //添加input代码
        add_file_input(index);

    };

    //添加file input
    function add_file_input(index) {

        var input_template = '<input type="file" name="image_file_{index}" id="image_file_{index}">';
        var input_html = input_template.format({index: index});
        var input_id = "input[id=image_file_" + index + "]";

        //替换HTML,必须用APPEND,用HTML()的话用户输入的值会消失
        $("#new-post-images-file").append(input_html);

        //监听change事件
        var input = $(input_id);
        input.on('change', function () {
            //验证文件名
            if( !this.value.match( /.jpg|.jpeg|.gif|.png|.bmp/i ) ){
                alert(this.value + ' - 图片格式无效！');
                return false;
            }
            //文件合格

            //预览
            add_preview(index, this);
            //计数+1
            that.images_count.add();
        });

        //弹出文件浏览对话框
        input.click();
    }


    //预览功能
    function add_preview(index, file) {
        var prevDiv = $('#new-post-images-preview');
        var image_id = "image-preview-" + index;

        //webkit
        if (file.files && file.files[0]) {
            var reader = new FileReader();
            reader.onload = function (evt) {

                prevDiv.append('<div class="image-preview" id="' + image_id + '"></div>');
                var preview_image = $("#" + image_id)
                preview_image.css('background-image', 'url(' + evt.target.result + ')');
                //在预览图上绑定鼠标悬停和点击事件
                bind_preview_event(preview_image, evt.target.result, file,false);

            };
            reader.readAsDataURL(file.files[0]);

            // Firefox
            if(!reader) {
                alert('Firfox');
                var preview_image = $("#" + image_id)
                preview_image.css('background-image', 'url(' + file.files[0].getAsDataURL() +')');
                //在预览图上绑定鼠标悬停和点击事件
                bind_preview_event(preview_image, evt.target.result, file,false);
            }

        }
        else {//ie
            //input的select()和document.selection.createRange().text非常关键，确保imgSrc获取到真实路径
            file.select();
            var imgSrc = document.selection.createRange().text;
            //alert(imgSrc);

            prevDiv.append('<div class="image-preview" id="' + image_id + '"></div>');
            var imageDiv = document.getElementById(image_id);
            imageDiv.style.filter = "progid:DXImageTransform.Microsoft.AlphaImageLoader(sizingMethod = scale)";
            imageDiv.filters("DXImageTransform.Microsoft.AlphaImageLoader").src = imgSrc;
            bind_preview_event($(imageDiv),imgSrc,file,true);
        }
    }


    // 在预览图上绑定鼠标悬停和点击事件
    function bind_preview_event(preview_image, image_url, file,isIE) {

        //添加鼠标悬停事件,改变图案
        preview_image.hover(function () {
                    //鼠标悬停状态,显示删除图标
                    $(this).css("background-image", "url(/static/other/del-image.png)");

                    //ie需要改变filter
                    if(isIE && this.style.filter)
                        this.style.filter="none";
                },//鼠标不悬停状态,恢复图片
                function () {

                    if(isIE){
                        //ie
                        this.style.filter = "progid:DXImageTransform.Microsoft.AlphaImageLoader(sizingMethod = scale)";
                        this.filters("DXImageTransform.Microsoft.AlphaImageLoader").src = image_url;
                    }
                    else//webkit
                        $(this).css('background-image', 'url(' + image_url + ')');

                });

        //添加鼠标点击事件,点击删除图片
        preview_image.on('click', function () {
            //alert('delete image' );
            preview_image.remove();
            $(file).remove();
            //计数器-1
            that.images_count.sub();
        });
    }

}



//显示回复框
function show_reply_area(event,comment_id){
    //alert(event.id)

    //遍历,将所有点击回复区设为display:none
    $('.new-reply-control-area').each(function(index,domEle){
        //alert(index)
        $(domEle).css('display','none');
    });

    //获取当前点击回复的input区
    //parents查找所有祖元素
    var cur_reply = $(event).parents('.comment-content').children('.new-reply-control-area');
    cur_reply.css('display','block');

    //var html_code = 'this is test html,comment_id:'+comment_id
    //cur_reply.html(html_code)
}

//投票
function vote(event,url,max_choice){

    var cur_poll = $(event).parents('.post-poll');
    //alert(cur_poll[0].className)


    //遍历,判断是否被选中
    var choice_ids = "";
    var choices_count = 0;

    //find查找所有后代元素
    cur_poll.find('.poll-option').each(function(){
        //alert(this.checked)
        if(this.checked){
            choice_ids += this.value+".";
            choices_count++;
        }
    });

    //判断投票数量
    if(choices_count == 0){
        alert('您还未选择投票选项,请至少选择一个。');
        return;
    }
    if(choices_count>max_choice){
        alert('投票超出数量,请重新选择。');
        return;
    }

    //js文件中无法使用jinja2模版引擎的函数
    //url = "{{ url_for('home.vote') }}"
    url += "?choice_ids="+choice_ids;
    url += "&from_url="+location.href;
    //alert(url)
    location.href=url;
}

<!-- lang: js -->
/**
 * 替换所有匹配exp的字符串为指定字符串
 * @param exp 被替换部分的正则
 * @param newStr 替换成的字符串
 */
String.prototype.replaceAll = function (exp, newStr) {
    return this.replace(new RegExp(exp, "gm"), newStr);
};

/**
 * 原型：字符串格式化
 * @param args 格式化参数值
 */
String.prototype.format = function(args) {
    var result = this;
    if (arguments.length < 1) {
        return result;
    }

    var data = arguments; // 如果模板参数是数组
    if (arguments.length == 1 && typeof (args) == "object") {
        // 如果模板参数是对象
        data = args;
    }
    for ( var key in data) {
        var value = data[key];
        if (undefined != value) {
            result = result.replaceAll("\\{" + key + "\\}", value);
        }
    }
    return result;
}


