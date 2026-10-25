import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeBackend} from './connection.mjs';
test('normalizes deployed HTTPS and LAN backend addresses',()=>{
 assert.equal(normalizeBackend(' https://gold.example/ '),'https://gold.example');
 assert.equal(normalizeBackend('http://192.168.1.5:8000/'),'http://192.168.1.5:8000');
 assert.equal(normalizeBackend('https://gold.example/api/'),'https://gold.example/api');
});
test('rejects invalid backend configuration',()=>{
 for(const value of ['', 'gold.example','ftp://gold.example','http://host:bad','https://user:password@gold.example','https://gold.example?token=x','https://gold.example/#fragment'])assert.throws(()=>normalizeBackend(value));
});
