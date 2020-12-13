import React from 'react'
import CanvasJSReact from '../assets/canvasjs.stock.react';
import {fetchShipnoiseData} from '../api/fetch';
var CanvasJSStockChart = CanvasJSReact.CanvasJSStockChart;

var dataPoints =[];

export default class Graph extends React.Component {
  constructor() {
    super();
    this.state = [{response: []}];
  }
  
  render() {
    const options = {
      title: {
          text: "ShipNoise Graph"
      },
      charts: [{
          data: [{
            type: "line",
            toolTipContent: "<b>Ship Name:</b> {name} <br/> <b>MMSI:</b> {mmsi} <hr/> <b>Noise:</b> {y}dB ",
            dataPoints: dataPoints
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
        <CanvasJSStockChart
          options={options}
          containerProps = {containerProps}
          onRef={ref => this.stockChart = ref}
        />
      </div>
    );
  }
  
  async componentDidMount() {
    var chart = this.stockChart;
    const data = await fetchShipnoiseData();
    
    for (var i = 0; i < data.length; i++) {
			dataPoints.push({
				x: new Date(data[i].date),
				y: data[i].noiseDelta,
				name: data[i].shipName,
				mmsi: data[i].shipMMSI
			});
		}
		chart.render();
  
  }
  
}