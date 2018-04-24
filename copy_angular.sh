#!/usr/bin/env bash

echo "inline.bundle"
cp ../crypto-daio-angular/dist/inline.*.bundle.js blocks/static/explorer-angular/inline.bundle.js
echo "main.bundle"
cp ../crypto-daio-angular/dist/main.*.bundle.js blocks/static/explorer-angular/main.bundle.js
echo "polyfill.bundle"
cp ../crypto-daio-angular/dist/polyfills.*.bundle.js blocks/static/explorer-angular/polyfills.bundle.js
echo "styles.bundle"
cp ../crypto-daio-angular/dist/styles.*.bundle.css blocks/static/explorer-angular/styles.bundle.css
