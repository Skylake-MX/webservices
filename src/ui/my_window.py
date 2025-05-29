import tkinter as tk

ventana=tk.Tk()

ventana.title("Encrypter/Decrypter")
ventana.geometry("800x400")
ventana.minsize(400,200)
ventana.maxsize(1920,1080)
ventana.configure()
ventana.attributes("-alpha",0.95)
# ventana.resizable(False,False)

frame1=tk.Frame(ventana, bg="lightblue")
frame1.configure(bg="red", width=400, height=200, bd=1)
frame1.pack()
#keyEntry=tk.Entry(ventana, width=50)
#keyEntry.pack()

etiqueta1=tk.Label(frame1, text="Etiqueta 1")
etiqueta1.config(fg="black", font=("Arial",12,"bold"))
etiqueta1.pack()

def xy_mouse(event):
    print(f"Cordenadas del mouse {event.x}, {event.y}")

ventana.bind("<a>", xy_mouse)
ventana.mainloop()
