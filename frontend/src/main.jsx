import React from 'react';
import {createRoot} from 'react-dom/client';
import {HashRouter} from 'react-router-dom';
import {AppProvider} from './state/AppContext';
import App from './App';
import './styles/global.css';
createRoot(document.getElementById('root')).render(<React.StrictMode><HashRouter><AppProvider><App/></AppProvider></HashRouter></React.StrictMode>);
