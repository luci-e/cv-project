var slides;
var currentSlide = 0;
var timers = [];
var framesPerSecond = 30;

var directions = {
    LEFT: 0,
    RIGHT: 1,
};

var timerStates = {
    PAUSED: 0,
    GOING: 1,
    FINISHED: 2,
};

class Timer {
    constructor(maxTime, bar) {
        this.state = timerStates.PAUSED;
        this.maxTime = parseFloat(maxTime);
        this.currentTime = 0;
        this.bar = bar;

        console.log(this.maxTime)
        console.log(this.bar)
    }

    pause() {
        this.state = timerStates.PAUSED;
        if (this.state == timerStates.PAUSED || this.state == timerStates.FINISHED) {
            return;
        }
        clearInterval(this.sliderInterval);
    }

    start() {
        switch (this.state) {
            case timerStates.GOING:
                {
                    return;
                }
            case timerStates.PAUSED:
                {
                    this.sliderInterval = setInterval(function() { slide(this); }.bind(this), 1000 / framesPerSecond);
                    this.state = timerStates.GOING;
                    return;
                }
            case timerStates.FINISHED:
                {
                    this.reset();
                    this.start();
                }
        }

    }

    reset() {
        this.pause();
        this.currentTime = 0;
        this.bar.width("0%");
    }
}

function slide(timer) {
    if (timer.currentTime <= timer.maxTime) {
        timer.bar.width(timer.currentTime * 100 / timer.maxTime + "%");
        timer.currentTime += 1 / framesPerSecond;
    } else {
        timer.bar.width("100%");
        timer.pause();
        timer.state = timerStates.FINISHED
    }
}

function moveSlides(direction) {
    if (direction == directions.LEFT) {
        if (currentSlide > 0) {
            slides[currentSlide].classList.add("slideWrap-none");
            slides[currentSlide - 1].classList.remove("slideWrap-none")
            currentSlide--;

        }
    } else if (direction == directions.RIGHT) {
        if (currentSlide < (slides.length - 1)) {
            slides[currentSlide].classList.add("slideWrap-none");
            slides[currentSlide + 1].classList.remove("slideWrap-none")
            currentSlide++;
        }
    }
}

function fillFixedFields() {
    var today = new Date();
    var dd = today.getDate();
    var mm = today.getMonth() + 1; //January is 0! As it should be
    var yyyy = today.getFullYear();

    if (dd < 10) { dd = '0' + dd }
    if (mm < 10) { mm = '0' + mm }

    today = yyyy + '/' + mm + '/' + dd;

    // Fill the fiexed fields
    $("div.inner_slide > .slide_content").each(function(i, element) {
        timer_bar = $($(element).find("[class='timer_bar']")[0]);
        timers[i] = new Timer(timer_bar.data("maxtime"), timer_bar);

        $(element).find("[class='inner_date']").html(today);
        $(element).find("[class='inner_pageno']").html("Page " + i);
        $(element).find("[class='inner_title_bot']").html($(element).find("[class='inner_title_top']").html());
    });

}

function keepFixedAspectRatio( event ){
    var win = $(this);

    var aspect_ratio = event.data.aspect_ratio;

    var win_height = win.height();
    var win_width = win.width();

    var current_ratio = win_width / win_height;

    if( current_ratio < aspect_ratio ){
        $('#slide_container').css({width: '100vw'});
        $('#slide_container').css({height: 1 / aspect_ratio * 100 + 'vw'});
        $('#slide_container').css('margin-top', (win_height - ( win_width / aspect_ratio)) / 2 + 'px');
        $('#slide_container').css('margin-left', 0);
    }else{
        $('#slide_container').css({height: '100vh'});
        $('#slide_container').css({width: aspect_ratio * 100 + 'vh'});
        $('#slide_container').css('margin-left', (win_width - ( win_height * aspect_ratio))/2 + 'px');
        $('#slide_container').css('margin-top', 0);
    }
}


window.onload = function() {
    slides = document.getElementsByClassName("slideWrap");
    fillFixedFields();
    $(window).on( 'resize', {aspect_ratio : 1.333 }, keepFixedAspectRatio ).trigger('resize');
};

document.onkeydown = function(evt) {
    evt = evt || window.event;
    switch (evt.keyCode) {
        case 37: // Left arrow
            {
                moveSlides(directions.LEFT);
                break;
            }
        case 39: // Right arrow
            {
                moveSlides(directions.RIGHT);
                timers[currentSlide - 1].start();
                break;
            }
        case 80: // P
            {
                timers[currentSlide - 1].pause();
                break;
            }
        case 82: // R
            {
                timers[currentSlide - 1].reset();
                break;
            }
        case 83: // S
            {
                timers[currentSlide - 1].start();
                break;
            }
    }
};