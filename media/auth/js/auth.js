$(document).ready(function() {
	$("#checkbox_none").click(function() {
		var checked_status = this.checked;
		$("input.checkbox").each(function() {
			this.checked = false;
		});
        return false;
	});		

	$("#checkbox_all").click(function() {
		var checked_status = this.checked;
		$("input.checkbox").each(function() {
			this.checked = true;
		});
        return false;
	});		

 	$("#checkbox_empty_pwd").click(function() {
		var checked_status = this.checked;
		$("input.empty_pwd").each(function() {
			this.checked = true;
		});
        return false;
	});
});