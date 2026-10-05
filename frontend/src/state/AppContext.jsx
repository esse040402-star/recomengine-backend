import {createContext,useContext,useEffect,useMemo,useReducer,useState} from 'react';
import {appReducer} from './appReducer';
import {readState,writeState} from '../utils/storage';
import E from '../services/preferenceEngine';
const AppContext=createContext(null);
export function AppProvider({children}){const [state,dispatch]=useReducer(appReducer,undefined,readState);const [storageError,setStorageError]=useState(false);useEffect(()=>{setStorageError(!writeState(state));},[state]);const analysis=useMemo(()=>E.report(state),[state]);return <AppContext.Provider value={{state,dispatch,analysis,storageError}}>{children}</AppContext.Provider>;}
export const useApp=()=>useContext(AppContext);
