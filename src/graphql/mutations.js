/* eslint-disable */
// this is an auto generated file. This will be overwritten

export const createShipnoise = /* GraphQL */ `
  mutation CreateShipnoise(
    $input: CreateShipnoiseInput!
    $condition: ModelShipnoiseConditionInput
  ) {
    createShipnoise(input: $input, condition: $condition) {
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
export const updateShipnoise = /* GraphQL */ `
  mutation UpdateShipnoise(
    $input: UpdateShipnoiseInput!
    $condition: ModelShipnoiseConditionInput
  ) {
    updateShipnoise(input: $input, condition: $condition) {
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
export const deleteShipnoise = /* GraphQL */ `
  mutation DeleteShipnoise(
    $input: DeleteShipnoiseInput!
    $condition: ModelShipnoiseConditionInput
  ) {
    deleteShipnoise(input: $input, condition: $condition) {
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
