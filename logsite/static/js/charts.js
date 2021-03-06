/*global PD,Chart, moment */
var ctx = document.getElementById("pdChart").getContext("2d");

function ts2str(ts) {
    var t = moment.unix(ts),
        tz = moment.tz.guess(),
        s = t.tz(tz).format("dddd LT z");
    return s;
}

function build() {
    var data = PD.recent.formats.PennyDreadful;
    var myChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: Object.keys(data).map(ts2str),
            datasets: [{
                label: "# Penny Dreadful Games",
                data: Object.values(data),
                borderWidth: 1
            }]
        },
        options: {
            scales: {
                yAxes: [{
                    ticks: {
                        beginAtZero:true
                    }
                }]
            }
        }
    });
}


function makeChart(data) {
    PD.recent = data;
    build();
}

$.get("/recent.json", makeChart);
