/* eslint-disable */
// this is an auto generated file. This will be overwritten

export const getShipnoise = /* GraphQL */ `
  query GetShipnoise($id: ID!) {
    getShipnoise(id: $id) {
      id
      type
      date
      noiseDelta
      shipName
      shipMMSI
      createdAt
      updatedAt
    }
  }
`;
export const listShipnoises = /* GraphQL */ `
  query ListShipnoises(
    $filter: ModelShipnoiseFilterInput
    $limit: Int
    $nextToken: String
  ) {
    listShipnoises(filter: $filter, limit: $limit, nextToken: $nextToken) {
      items {
        id
        type
        date
        noiseDelta
        shipName
        shipMMSI
        createdAt
        updatedAt
      }
      nextToken
    }
  }
`;
export const listShipnoiseByDate = /* GraphQL */ `
  query ListShipnoiseByDate(
    $type: String
    $date: ModelStringKeyConditionInput
    $sortDirection: ModelSortDirection
    $filter: ModelShipnoiseFilterInput
    $limit: Int
    $nextToken: String
  ) {
    listShipnoiseByDate(
      type: $type
      date: $date
      sortDirection: $sortDirection
      filter: $filter
      limit: $limit
      nextToken: $nextToken
    ) {
      items {
        id
        type
        date
        noiseDelta
        shipName
        shipMMSI
        createdAt
        updatedAt
      }
      nextToken
    }
  }
`;
