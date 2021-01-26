# ShipNoise.Net

This repo specifies the web backend and frontend for the ShipNoise prototype site, a way to visualize the noisiest ships in the Salish Sea.

The demo site can be found here: https://main.d27wklsx9a9q36.amplifyapp.com/

## Contributing

Please check out the CONTRIBUTING doc for tips on making a successful contribution.

## How it works

At this stage, this repo is merely a prototype for the real ShipNoise.Net, a proof-of-concept for future development. 
It is automatically deployed to the AWS Amplify environment from this repo's main branch. Pushes to the main branch trigger a new deployment.

The demo site is available at: https://main.d27wklsx9a9q36.amplifyapp.com/ 

## Architecture

We are using [AWS Amplify](https://aws.amazon.com/amplify/), which is a suite of tools and services that is used to build full-stack applications. 
Here is a basic description of the architecture:

- The frontend is built using React
- We use the [GraphQL](https://graphql.org/) API, which leverages AWS AppSync and is backed by DynamoDB
- The ShipNoise data will be stored in [DynamoDB](https://aws.amazon.com/dynamodb/)

Note: At this stage of development, the ShipNoise data processing is still not connected to DynamoDB. As of this writing, this app is mostly just 
a skeleton full-stack application with dummy data to provide a proof-of-concept for future development.
In the future we will be pushing the real hydrophone and AIS data to DynamoDB for retrieval by the site.

## Running the code locally

In the project directory, you can run:

### `yarn start`

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

The page will reload if you make edits.\
You will also see any lint errors in the console.
