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
		$("input.none").each(function() {
			this.checked = true;
		});
        return false;
    });
    $("#checkbox_core").click(function() {
		$("input.core").each(function() {
			this.checked = true;
		});
        return false;
    });
    $("#checkbox_local_current").click(function() {
		$("input.local_current").each(function() {
			this.checked = true;
		});
        return false;
    });
    $("#checkbox_local_classic").click(function() {
		$("input.local_classic").each(function() {
			this.checked = true;
		});
        return false;
    });
    $("#checkbox_heavy_rotation").click(function() {
		$("input.heavy_rotation").each(function() {
			this.checked = true;
		});
        return false;
    });
    $("#checkbox_light_rotation").click(function() {
		$("input.light_rotation").each(function() {
			this.checked = true;
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
        $("input[name=mark_as]").val('none');
        $(this).parents("form").submit();
        return false;
    });
    $("#mark_core").click(function() {
        $("input[name=mark_as]").val('core');
        $(this).parents("form").submit();
        return false;
    });
    $("#mark_local_current").click(function() {
        $("input[name=mark_as]").val('local_current');
        $(this).parents("form").submit();
        return false;
    });
    $("#mark_local_classic").click(function() {
        $("input[name=mark_as]").val('local_classic');
        $(this).parents("form").submit();
        return false;
    });
    $("#mark_heavy_rotation").click(function() {
        $("input[name=mark_as]").val('heavy_rotation');
        $(this).parents("form").submit();
        return false;
    });
    $("#mark_light_rotation").click(function() {
        $("input[name=mark_as]").val('light_rotation');
        $(this).parents("form").submit();
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
});
