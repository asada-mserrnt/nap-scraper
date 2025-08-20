name: nap

on:
  workflow_dispatch:
  schedule:
    - cron: '0 0 * * *'

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.9"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run napp_scraper.py
        env:
          NAP_CAMPSITE_ID: ${{ secrets.NAP_CAMPSITE_ID }}
          NAP_STAFF_ID: ${{ secrets.NAP_STAFF_ID }}
          NAP_PASSWORD: ${{ secrets.NAP_PASSWORD }}
        run: python napp_scraper.py

      - name: Trigger GAS import
        run: |
          if [ -n "${{ secrets.GAS_WEBAPP_URL }}" ] && [ -n "${{ secrets.GAS_TOKEN }}" ]; then
            curl -X POST "${{ secrets.GAS_WEBAPP_URL }}?token=${{ secrets.GAS_TOKEN }}"
          else
            echo "GAS_WEBAPP_URL or GAS_TOKEN not set; skipping."
          fi
