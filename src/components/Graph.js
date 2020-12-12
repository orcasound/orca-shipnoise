import React from 'react'
import CanvasJSReact from '../assets/canvasjs.stock.react';
import {shipnoiseData} from '../constants/shipnoiseData';
var CanvasJSStockChart = CanvasJSReact.CanvasJSStockChart;

export default class Graph extends React.Component {
    render() {
      //TODO: fetch from API instead of const
    var dataPoints = shipnoiseData;
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
  
}