/* App.js */

import CanvasJSReact from './canvasjs.stock.react';
var React = require('react');
var Component = React.Component;
var CanvasJS = CanvasJSReact.CanvasJS;
var CanvasJSStockChart = CanvasJSReact.CanvasJSStockChart;

 
export default class App extends Component {
  render() {
    const options = {
      title: {
          text: "ShipNoise Graph"
      },
      charts: [{
          data: [{
            type: "line",
            dataPoints: [
	      { x: new Date("2018-01-01Z00:00"), y: 71 },
	      { x: new Date("2018-01-01Z00:01"), y: 55 },
	      { x: new Date("2018-01-01Z00:02"), y: 50 },
	      { x: new Date("2018-01-01Z00:03"), y: 65 },
	      { x: new Date("2018-01-01Z00:04"), y: 95 },
	      { x: new Date("2018-01-01Z00:05"), y: 68 },
	      { x: new Date("2018-01-01Z00:06"), y: 28 },
	      { x: new Date("2018-01-01Z00:07"), y: 34 },
	      { x: new Date("2018-01-01Z00:08"), y: 14 },
	      { x: new Date("2018-01-01Z00:09"), y: 71 },
	      { x: new Date("2018-01-01Z00:10"), y: 55 },
	      { x: new Date("2018-01-01Z00:11"), y: 50 },
	      { x: new Date("2018-01-01Z00:12"), y: 34 },
	      { x: new Date("2018-01-01Z00:13"), y: 50 },
	      { x: new Date("2018-01-01Z00:14"), y: 50 },
	      { x: new Date("2018-01-01Z00:15"), y: 95 },
	      { x: new Date("2018-01-01Z00:16"), y: 68 },
	      { x: new Date("2018-01-01Z00:17"), y: 28 },
	      { x: new Date("2018-01-01Z00:18"), y: 34 },
	      { x: new Date("2018-01-01Z00:19"), y: 65 },
	      { x: new Date("2018-01-01Z00:20"), y: 55 },
	      { x: new Date("2018-01-01Z00:21"), y: 71 },
	      { x: new Date("2018-01-01Z00:22"), y: 55 },
	      { x: new Date("2018-01-01Z00:23"), y: 50 }
	  ]
         }]
      }],
      navigator: {
        slider: {
          minimum: new Date("2018-01-01"),
          maximum: new Date("2018-01-02")
        }
      }
    };
    const containerProps = {
      width: "80%",
      height: "450px",
      margin: "auto"
    };
    return (
      <div>
      <h1>ShipNoise.net</h1>
      <h3>Characterizing ship noise in orca habitats</h3>
      
      <p>Ship noise dominates the acoustic habitat of the Southern Resident Orca Whales within the Salish Sea.</p>
      <p>What did the orca whales hear today in Puget Sound?</p>
        <CanvasJSStockChart
          options={options}
          containerProps = {containerProps}
          onRef={ref => this.stockChart = ref}
        />
      </div>
    );
  }
}