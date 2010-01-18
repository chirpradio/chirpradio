$(document).ready(function() {
	$("#checkbox_none").click(function() {
		$("input.checkbox").each(function() {
			this.checked = false;
		});
        return false;
	});		
	$("#checkbox_all").click(function() {
		$("input.checkbox").each(function() {
			this.checked = true;
		});
        return false;
	});		
    $("#checkbox_nocat").click(function() {
        $("select").each(function() {
            if (this[0].selected == "1") {
                var strs = this.name.split("_");
                var elements = document.getElementsByName("checkbox_" + strs[1]);
                for (var i = 0; i < elements.length; i++) {
                    elements[i].checked = true;
                }
            }
        });
        return false;
    });
    $("#checkbox_core").click(function() {
        $("select").each(function() {
            if (this[1].selected == "1") {
                var strs = this.name.split("_");
                var elements = document.getElementsByName("checkbox_" + strs[1]);
                for (var i = 0; i < elements.length; i++) {
                    elements[i].checked = true;
                }
            }
        });
        return false;
    });
    $("#checkbox_local_current").click(function() {
        $("select").each(function() {
            if (this[2].selected == "1") {
                var strs = this.name.split("_");
                var elements = document.getElementsByName("checkbox_" + strs[1]);
                for (var i = 0; i < elements.length; i++) {
                    elements[i].checked = true;
                }
            }
        });
        return false;
    });
    $("#checkbox_local_classic").click(function() {
        $("select").each(function() {
            if (this[3].selected == "1") {
                var strs = this.name.split("_");
                var elements = document.getElementsByName("checkbox_" + strs[1]);
                for (var i = 0; i < elements.length; i++) {
                    elements[i].checked = true;
                }
            }
        });
        return false;
    });
    $("#checkbox_heavy").click(function() {
        $("select").each(function() {
            if (this[4].selected == "1") {
                var strs = this.name.split("_");
                var elements = document.getElementsByName("checkbox_" + strs[1]);
                for (var i = 0; i < elements.length; i++) {
                    elements[i].checked = true;
                }
            }
        });
        return false;
    });
    $("#checkbox_light").click(function() {
        $("select").each(function() {
            if (this[5].selected == "1") {
                var strs = this.name.split("_");
                var elements = document.getElementsByName("checkbox_" + strs[1]);
                for (var i = 0; i < elements.length; i++) {
                    elements[i].checked = true;
                }
            }
        });
        return false;
    });
	$("#checkbox_explicit").click(function() {
		$("input.explicit").each(function() {
			this.checked = true;
		});
        return false;
	});		
	$("#checkbox_recommended").click(function() {
		$("input.recommended").each(function() {
			this.checked = true;
		});
        return false;
	});		
    
    $("#mark_nocat").click(function() {
        $("input.checkbox").each(function() {
            if (this.checked == true) {
                var strs = this.name.split("_");
                var elements = document.getElementsByName("category_" + strs[1]);
                for (var i = 0; i < elements.length; i++) {
                    elements[i][0].selected = "1";
                }
            }
        });
        return false;
    });
    $("#mark_core").click(function() {
        $("input.checkbox").each(function() {
            if (this.checked == true) {
                var strs = this.name.split("_");
                var elements = document.getElementsByName("category_" + strs[1]);
                for (var i = 0; i < elements.length; i++) {
                    elements[i][1].selected = "1";
                }
            }
        });
        return false;
    });
    $("#mark_local_current").click(function() {
        $("input.checkbox").each(function() {
            if (this.checked == true) {
                var strs = this.name.split("_");
                var elements = document.getElementsByName("category_" + strs[1]);
                for (var i = 0; i < elements.length; i++) {
                    elements[i][2].selected = "1";
                }
            }
        });
        return false;
    });
    $("#mark_local_classic").click(function() {
        $("input.checkbox").each(function() {
            if (this.checked == true) {
                var strs = this.name.split("_");
                var elements = document.getElementsByName("category_" + strs[1]);
                for (var i = 0; i < elements.length; i++) {
                    elements[i][3].selected = "1";
                }
            }
        });
        return false;
    });
    $("#mark_heavy").click(function() {
        $("input.checkbox").each(function() {
            if (this.checked == true) {
                var strs = this.name.split("_");
                var elements = document.getElementsByName("category_" + strs[1]);
                for (var i = 0; i < elements.length; i++) {
                    elements[i][4].selected = "1";
                }
            }
        });
        return false;
    });
    $("#mark_light").click(function() {
        $("input.checkbox").each(function() {
            if (this.checked == true) {
                var strs = this.name.split("_");
                var elements = document.getElementsByName("category_" + strs[1]);
                for (var i = 0; i < elements.length; i++) {
                    elements[i][5].selected = "1";
                }
            }
        });
        return false;
    });
    $("#mark_explicit").click(function() {
        $("input[name=mark_as]").val('explicit');
        $(this).parents("form").submit();
        return false;
    });
    $("#mark_recommended").click(function() {
        $("input[name=mark_as]").val('recommended');
        $(this).parents("form").submit();
        return false;
    });

    $("#sortable").sortable({
        update : function() {
            var order = $("#sortable").sortable('serialize');
            $("#reorder").load("/djdb/crate/reorder?" + order);
        }
    });
//	$("#sortable").disableSelection();

    var default_opt = {
    };
    
    $("#id_user").autocomplete("/auth/search.txt", 
        $.extend({
            onItemSelect: function(li) {
                var entity_key = li.extra[0];
                $("#id_user_key").attr("value", entity_key);
                $("#id_user").focus();
            }
        }, default_opt));
    
    // be sure that freeform entry always clears out any 
    // previously auto-completed keys :
    $("#id_user").change(function() {
        $("#id_user_key").attr("value", "");
    });
});