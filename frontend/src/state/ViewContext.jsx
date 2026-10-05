import {createContext,useContext} from 'react';
export const ViewContext=createContext(null);
export const useView=()=>useContext(ViewContext);
