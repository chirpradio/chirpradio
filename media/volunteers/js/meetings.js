// requires: chirp/chirp.js

$(document).ready(function() {
	// test test    
    var attendee_list_ul, 
        meeting_id, 
        attendee_user_ids = [], 
        show_all = false,
        show_max = 15;
    
    
    var do_hide_excess = function() {
        var count = $('li', attendee_list_ul).length;
        $('li', attendee_list_ul).slice(0, count-show_max).css("display","none");
    };
    
    var set_hide_excess = function() {
        $("#attendee_list_display").text("(hide some)").click(function() {
            show_all = false;
            do_hide_excess();
            set_show_all();
        });
    };
    
    var do_show_all = function() {
        $('li', attendee_list_ul).css("display","list-item");
    };
    
    var set_show_all = function() {
        $("#attendee_list_display").text("(show all)").click(function() {
            show_all = true;
            do_show_all();
            set_hide_excess();
        });
    };
        
    var render_list_control = function() {
        var count = $('li', attendee_list_ul).length;
        $("#attendee_count").text(count+" attendee"+(count==1?'':'s')+" ");
        if (count > show_max) {
            if (show_all) {
                do_show_all();
                set_hide_excess();
            } else {
                do_hide_excess();
                set_show_all();
            }
        }
    };
    
    var Attendee = function(config) {
        if (!meeting_id) {
            alert("Select a meeting date before adding attendees.");
            return;
        }
        this.meeting_id = meeting_id;
        this.name = config.name;
        this.user_id = config.user_id;
        this.do_save = config.do_save; // was new record
        this.ul; // the ul elem
        if (!this.exists()) {
            this.add();   
        }
    }
    
    Attendee.prototype.exists = function() {
        var that = this;
        return ($.inArray(that.user_id, attendee_user_ids) != -1) || false;
    }
    
    Attendee.prototype.add = function() {
        var that = this;
        
        if (!attendee_list_ul) {
            attendee_list_ul = $(document.createElement("ul"));
            $("#attendee_list").append(attendee_list_ul);
        }
        that.ul = attendee_list_ul;
        var li = $(document.createElement("li"))
            .attr("id", that.htmlId())
            .html(
                that.name + ' <a href="#">[x]</a>'
		  );
        $("a", li).click(function(e) {
            that.delete();
            e.preventDefault();
        });
        attendee_list_ul.append(li);
        attendee_user_ids.push(that.user_id);
        render_list_control();
        if (that.do_save) {
            that.save();
        }
    }
    
    Attendee.prototype.save = function() {
        var that = this;
        chirp.request({
            url: chirp.url('chirp/meetings/'+that.meeting_id+'/attendee/add/'+that.user_id+'.json'),
            success: function(response) {
            }
        });
    }
    
    Attendee.prototype.delete = function() {
        var that = this;
        chirp.request({
            url: chirp.url('chirp/meetings/'+that.meeting_id+'/attendee/delete/'+that.user_id+'.json'),
            success: function(response) {
                $("#" + that.htmlId(), that.ul).remove();
                var i = attendee_user_ids.indexOf(that.user_id);
                attendee_user_ids.pop(i);
                render_list_control();
            }
        })
    }
    
    Attendee.prototype.htmlId = function() {
        return "attendee_list-" + this.user_id;
    }
    
    $("#attendee_name").autocomplete("/chirp/search_users", {
        selectFirst: true,
        onItemSelect: function(li) {
            var user_id = parseInt(li.extra[0]);
            var attendee = new Attendee({name: li.innerHTML, user_id: user_id, do_save:true});
            $("#attendee_name").attr("value", "").focus();
        }
    });
    
    $("#meeting_date").datepicker({
        dateFormat: 'mm/dd/yy', // note yy is YYYY (i.e. 2009)
        onSelect: function(dateText) {
            chirp.request({
                url: chirp.url('chirp/meetings/' + dateText + '/track.json'),
                success: function(response) {
                    meeting_id = response.meeting_id;
                    attendee_user_ids = [];
                    $("#attendee_list li").remove();
                    $.map(response.attendees, function(user) {
                        var attendee = new Attendee({name:user.name, user_id:user.user_id})
                    });
                    render_list_control();
                }
            })
        }
    });
});