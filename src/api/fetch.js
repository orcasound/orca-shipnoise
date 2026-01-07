import { API } from 'aws-amplify';
import {listShipnoiseByDate} from '../graphql/queries';

export async function fetchShipnoiseData() {
    const response = await API.graphql({ query: listShipnoiseByDate, variables: {type: "Set", sortDirection: "DESC"} });
    return response.data.listShipnoiseByDate.items;
}