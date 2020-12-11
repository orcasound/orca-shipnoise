import React, {Component} from 'react'
import CanvasJSReact from '../assets/canvasjs.stock.react';
var CanvasJS = CanvasJSReact.CanvasJS;
var CanvasJSStockChart = CanvasJSReact.CanvasJSStockChart;

var dataPoints = [];

export default class Graph extends React.Component {
    render() {
    const options = {
      title: {
          text: "ShipNoise Graph"
      },
      charts: [{
          data: [{
            type: "line",
            toolTipContent: "<b>Ship Name:</b> {name} <br/> <b>MMSI:</b> {mmsi} <hr/> <b>Noise:</b> {y}dB ",
            //TODO: pull this from the API
            dataPoints: [
	      { x: new Date("2018-01-01Z00:00"), y: 71, name: "HMS Pinafore", mmsi: 12345 },
	      { x: new Date("2018-01-01Z00:01"), y: 55, name: "Boaty McBoatFace", mmsi: 6789 },
	      { x: new Date("2018-01-01Z00:02"), y: 50, name: "HMS Pinafore", mmsi: 12345 },
	      { x: new Date("2018-01-01Z00:03"), y: 65, name: "Seas the Day", mmsi: 6789 },
	      { x: new Date("2018-01-01Z00:04"), y: 95, name: "HMS Pinafore", mmsi: 12345 },
	      { x: new Date("2018-01-01Z00:05"), y: 68, name: "Boaty McBoatFace", mmsi: 6789 },
	      { x: new Date("2018-01-01Z00:06"), y: 28, name: "HMS Pinafore", mmsi: 6789 },
	      { x: new Date("2018-01-01Z00:07"), y: 34, name: "Seas the Day", mmsi: 12345 },
	      { x: new Date("2018-01-01Z00:08"), y: 14, name: "HMS Pinafore", mmsi: 6789 },
	      { x: new Date("2018-01-01Z00:09"), y: 71, name: "HMS Pinafore", mmsi: 12345 },
	      { x: new Date("2018-01-01Z00:10"), y: 55, name: "Boaty McBoatFace", mmsi: 6789 },
	      { x: new Date("2018-01-01Z00:11"), y: 50, name: "HMS Pinafore", mmsi: 12345 },
	      { x: new Date("2018-01-01Z00:12"), y: 34, name: "HMS Pinafore", mmsi: 6789 },
	      { x: new Date("2018-01-01Z00:13"), y: 50, name: "HMS Pinafore", mmsi: 12345 },
	      { x: new Date("2018-01-01Z00:14"), y: 50, name: "Seas the Day", mmsi: 6789 },
	      { x: new Date("2018-01-01Z00:15"), y: 95, name: "HMS Pinafore", mmsi: 12345 },
	      { x: new Date("2018-01-01Z00:16"), y: 68, name: "HMS Pinafore", mmsi: 6789 },
	      { x: new Date("2018-01-01Z00:17"), y: 28, name: "Boaty McBoatFace", mmsi: 12345 },
	      { x: new Date("2018-01-01Z00:18"), y: 34, name: "HMS Pinafore", mmsi: 6789 },
	      { x: new Date("2018-01-01Z00:19"), y: 65, name: "Seas the Day", mmsi: 12345 },
	      { x: new Date("2018-01-01Z00:20"), y: 55, name: "Boaty McBoatFace", mmsi: 6789 },
	      { x: new Date("2018-01-01Z00:21"), y: 71, name: "HMS Pinafore", mmsi: 12345 },
	      { x: new Date("2018-01-01Z00:22"), y: 55, name: "Seas the Day", mmsi: 6789 },
	      { x: new Date("2018-01-01Z00:23"), y: 50, name: "HMS Pinafore", mmsi: 12345 }
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
        <CanvasJSStockChart
          options={options}
          containerProps = {containerProps}
          onRef={ref => this.stockChart = ref}
        />
      </div>
    );
  }
  
}