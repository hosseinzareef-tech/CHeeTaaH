import threading
import asyncio
import json
import zlib
import websockets
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock

class CheetahUltraApp(App):
    def build(self):
        self.title = "CheeTaH Sniper Engine"
        
        layout = BoxLayout(orientation='vertical', padding=10, spacing=5)
        
        layout.add_widget(Label(text='Target Pair:', size_hint_y=None, height=20, font_size=14))
        self.pair_input = TextInput(text='btc_usdt', multiline=False, size_hint_y=None, height=40, font_size=16)
        layout.add_widget(self.pair_input)
        
        self.start_btn = Button(text='START SNIPER ENGINE', size_hint_y=None, height=40, background_color=(0.1, 0.6, 0.3, 1), font_size=16, bold=True)
        self.start_btn.bind(on_press=self.start_engine)
        layout.add_widget(self.start_btn)
        
        # بخش نمایشگر اطلاعات با ۴ لیبل مجزا برای نظم کامل و فونت غول‌پیکر
        self.display_box = BoxLayout(orientation='vertical', size_hint_y=1, padding=2, spacing=2)
        
        self.signal_lbl = Label(text='WAITING...', font_size=160, bold=True, halign='center', valign='middle', markup=True)
        self.price_lbl = Label(text='', font_size=100, bold=True, halign='center', valign='middle', markup=True)
        self.tp_lbl = Label(text='', font_size=90, bold=True, halign='center', valign='middle', markup=True)
        self.sl_lbl = Label(text='', font_size=90, bold=True, halign='center', valign='middle', markup=True)
        
        for lbl in [self.signal_lbl, self.price_lbl, self.tp_lbl, self.sl_lbl]:
            lbl.bind(size=lbl.setter('text_size'))
            self.display_box.add_widget(lbl)
            
        layout.add_widget(self.display_box)
        
        self.running = False
        return layout

    def start_engine(self, instance):
        if not self.running:
            self.running = True
            self.start_btn.text = 'SNIPER RUNNING...'
            self.start_btn.background_color = (0.8, 0.2, 0.2, 1)
            target_pair = self.pair_input.text.strip().lower()
            threading.Thread(target=self.run_async_loop, args=(target_pair,), daemon=True).start()

    def run_async_loop(self, pair):
        asyncio.run(self.websocket_worker(pair))

    async def websocket_worker(self, user_pair):
        uri = "wss://api.lbank.info/ws/V2/"
        
        while self.running:
            try:
                async with websockets.connect(uri, ping_interval=20, ping_timeout=20) as websocket:
                    sub_msg = {
                        "action": "subscribe",
                        "subscribe": "depth",
                        "pair": user_pair,
                        "depth": "50"
                    }
                    await websocket.send(json.dumps(sub_msg))
                    
                    while self.running:
                        response = await websocket.recv()
                        if isinstance(response, bytes):
                            decompressed = zlib.decompress(response, 16 + zlib.MAX_WBITS)
                            data = json.loads(decompressed.decode('utf-8'))
                        else:
                            data = json.loads(response)
                        
                        if "ping" in data:
                            await websocket.send(json.dumps({"pong": data["ping"]}))
                            continue
                        
                        depth_data = data.get("depth", {})
                        bids = depth_data.get("bids", [])
                        asks = depth_data.get("asks", [])
                        if not bids or not asks:
                            continue
                        
                        mid_price = float(bids[0][0])
                        
                        total_bid_vol = sum([float(b[1]) for b in bids[:10]])
                        total_ask_vol = sum([float(a[1]) for a in asks[:10]])
                        
                        if total_bid_vol > total_ask_vol * 1.3:
                            sig_txt = "[color=00ff66]BUY[/color]"
                            tp = mid_price * 1.015
                            sl = mid_price * 0.992
                        elif total_ask_vol > total_bid_vol * 1.3:
                            sig_txt = "[color=ff3333]SELL[/color]"
                            tp = mid_price * 0.985
                            sl = mid_price * 1.008
                        else:
                            sig_txt = "[color=cccccc]NEUTRAL[/color]"
                            tp = 0
                            sl = 0

                        if tp > 0:
                            p_txt = f"[color=ffffff]Price: {mid_price:,.1f}[/color]"
                            tp_txt = f"[color=00ffcc]TP: {tp:,.1f}[/color]"
                            sl_txt = f"[color=ff9999]SL: {sl:,.1f}[/color]"
                        else:
                            p_txt = f"[color=ffffff]Price: {mid_price:,.1f}[/color]"
                            tp_txt = ""
                            sl_txt = ""

                        Clock.schedule_once(lambda dt, s=sig_txt, p=p_txt, t=tp_txt, l=sl_txt: self.update_ui(s, p, t, l), 0)
                        await asyncio.sleep(1)
            except Exception as e:
                err_txt = "[color=ffff00]RECONNECTING...[/color]"
                Clock.schedule_once(lambda dt, s=err_txt, p="", t="", l="": self.update_ui(s, p, t, l), 0)
                await asyncio.sleep(3)

    def update_ui(self, s, p, t, l):
        self.signal_lbl.text = s
        self.price_lbl.text = p
        self.tp_lbl.text = t
        self.sl_lbl.text = l

if __name__ == '__main__':
    CheetahUltraApp().run()
