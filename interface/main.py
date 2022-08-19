from typing import Union

from kivy.core.window import Window
from kivymd.app import MDApp as App
from kivymd.uix.boxlayout import MDBoxLayout as BoxLayout
from kivymd.uix.button import MDRaisedButton as Button
from kivymd.uix.widget import MDWidget as Widget
from kivymd.uix.slider.slider import MDSlider as Slider
from kivymd.uix.label.label import Label
from kivymd.uix.pickers.colorpicker.colorpicker import MDColorPicker
from kivy.clock import Clock
from kivy.garden.joystick import Joystick # type: ignore

from input_handler import InputHandler, Message


input_handler = InputHandler()

class ControllerLayout(Widget):
    def __init__(self):
        super().__init__()

        vertical_box_layout = BoxLayout(orientation="vertical")
        horizontal_box_layout = BoxLayout(orientation="horizontal", size=Window.size)
        
        def _joystick_handle(_, pad):
            message = Message(direction=pad)
            input_handler.queue_message(message)
            print("queued")
            
        joystick = Joystick()
        joystick.bind(pad=_joystick_handle)

        def _emergency_stop(_):
            message = Message(stop=True)
            input_handler.force_send(message)

        emergency_stop_button = Button(text="Emergency Stop", on_press=_emergency_stop, size_hint=(1, 0.5), font_size="100sp")
        distance_label = Label(text="No Distance Received", font_size="60sp", color=(200, 200, 200))

        def _distance_recv(message: Message):
            if message.distance is not None:
                distance_label.text = "Distance Reading: " + str(message.distance)

        input_handler.add_listen_callback(_distance_recv)

        vertical_box_layout.add_widget(distance_label)
        vertical_box_layout.add_widget(joystick)
        vertical_box_layout.add_widget(emergency_stop_button)

        horizontal_box_layout.add_widget(vertical_box_layout)

        speed_slider = Slider(orientation="vertical", size_hint=(0.10, 1))
        horizontal_box_layout.add_widget(speed_slider)

        self.add_widget(horizontal_box_layout)

        # create a clock to check the slider every 0.15 seconds
        def _check_slider(_):
            input_handler.handle_speed_slider(speed_slider)
        
        Clock.schedule_interval(_check_slider, 0.15)

class ControllerApp(App):
    def build(self):
        return ControllerLayout()

if __name__ == "__main__":
    ControllerApp().run()
