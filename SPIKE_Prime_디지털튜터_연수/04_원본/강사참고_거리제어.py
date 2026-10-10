# 공식 SPIKE 3 계열 예제를 참고한 작성 코드. 실물 Hub 실행 미검증.
# A 왼쪽 모터, E 오른쪽 모터, B 거리센서. 실제 앞 방향을 먼저 확인하세요.
from hub import port
import runloop, motor_pair, distance_sensor

async def main():
    motor_pair.pair(motor_pair.PAIR_1, port.A, port.E)
    while True:
        d = distance_sensor.distance(port.B)
        if d == -1 or d < 200:
            motor_pair.stop(motor_pair.PAIR_1)
        else:
            motor_pair.move(motor_pair.PAIR_1, 0, velocity=200)
        await runloop.sleep_ms(20)

runloop.run(main())
