

google.load("jquery", "1");
google.load("jqueryui", "1");

function OnLoad(){
  $('#content').html('<div id="draggable-handle-div" style="width:100px;border:1px solid #999;">' +
                     '<div style="background-color:#999">dragme</div>content</div>');
  $("#draggable-handle-div").draggable({
    "handle": "div"
  });
}

google.setOnLoadCallback(OnLoad);