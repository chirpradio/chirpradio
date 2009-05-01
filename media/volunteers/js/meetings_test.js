
$(function() {

$('body').prepend(
    // '<h1 id="header">' + document.title + '</h1>' +
    // '<h2 id="banner"></h2>' +
    '<h2 id="userAgent"></h2>' +
    '<ol id="tests"></ol>' + 
    '<div id="main"></div>'
);

});

function _sleep(ms_delay) {
    // sort of CPU intensive and probably better to use deferred tests.
    var start = new Date().getTime();
    while (new Date().getTime() < start + ms_delay);
}

$(document).ready(function() {
    
    //
    // Well, hmm, I am giving up getting these tests to work.
    //
    
    // http://www.kodyaz.com/content/HowToGetKeyCodesList.aspx
    var keys = {
        F: 70,
        ENTER: 13,
        // ENTER: $.simulate.VK_ENTER,
        // TAB: $.simulate.VK_TAB
        TAB: 9
    };
    
    // failed experiment:
    /*
    var datepick = $("#meeting_date")[0];
    
    fireunit.value(datepick, "");
    fireunit.mouseDown( datepick );
    fireunit.click( datepick );
    fireunit.focus( datepick );
    
    setTimeout(function(){
        // Finish test
        fireunit.key( $("#meeting_date")[0], keys.ENTER );
        fireunit.testDone();
    }, 2000);
    */
    
    module("Test");
    
    test("select date", function() {
        
        var selectedThis;
        
        function callback(date, inst) {
            selectedThis = this;
            selectedDate = date;
            selectedInst = inst;        
        }
        
         var inp = $('#meeting_date');
         var date = new Date();
         // onSelect
         inp.val('').datepicker('show')
             .simulate('keydown', {keyCode: $.simulate.VK_ENTER})
                 ;
     
        // _sleep(1000);
    });
    
    test("add attendee", function() {
        var input = $("#attendee_name");
        
        input
            .simulate('keydown', {keyCode: keys.F}) // trigger setTimeOut in autocomplete
            .simulate('focus')
            .val("fred") // type some stuff
            // .simulate('keydown', {keyCode: keys.TAB})
                ;
        // _sleep(3000);
       
       input
            // .simulate('blur')
            // .simulate('keydown', {keyCode: keys.ENTER})
                ; 
    });
    
});