from src.common.state import State


def show_menu():
    print("=== 選課與課表規劃系統 ===")
    print("1 課程管理")
    print("2 選課")
    print("0 離開")


def main():
    state = State()
    while True:
        show_menu()
        choice = input("請選擇：").strip()
        if choice == "0":
            print("再見")
            break
        elif choice == "1":
            print("（課程管理，待完成）")
        elif choice == "2":
            print("（選課，待完成）")
        else:
            print("無效的選項")


if __name__ == "__main__":
    main()