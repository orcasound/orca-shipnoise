/* App.js */

import Graph from './components/Graph';
var React = require('react');
var Component = React.Component;
 
export default class App extends Component {
  render() {
    return (
      <div>
      <h1>ShipNoise.net</h1>
      <h3>Characterizing ship noise in orca habitats</h3>
      
      <p>Ship noise dominates the acoustic habitat of the Southern Resident Orca Whales within the Salish Sea.</p>
      <p>What did the orca whales hear today in Puget Sound?</p>
      <Graph />
      </div>
    );
  }
}