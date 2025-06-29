from __future__ import annotations
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, WorkerOptions, cli, function_tool, RunContext
from livekit.plugins import google, noise_cancellation
from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION, LOOKUP_RESERVATION_MESSAGE
from db_driver import DatabaseDriver
import enum, logging

load_dotenv()
logger = logging.getLogger("user-data")
logger.setLevel(logging.INFO)
DB = DatabaseDriver()

class ReservationDetails(enum.Enum):
    NAME = "name"
    PHONE = "phone"
    DATE = "date"
    TIME = "time"
    GUESTS = "guests"

class RestaurantAgent(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=AGENT_INSTRUCTION)
        self._reservation: dict[ReservationDetails, str] = {
            ReservationDetails.NAME: "",
            ReservationDetails.PHONE: "",
            ReservationDetails.DATE: "",
            ReservationDetails.TIME: "",
            ReservationDetails.GUESTS: ""
        }

    def has_reservation(self):
        return self._reservation[ReservationDetails.PHONE] != ""

    def get_reservation_str(self):
        return "\n".join(f"{k.value}: {v}" for k, v in self._reservation.items())

    @function_tool()
    async def lookup_reservation(self, context: RunContext, phone: str) -> str:
        result = DB.get_reservation_by_phone(phone)
        if not result:
            return "Reservation not found"
        self._reservation = {
            ReservationDetails.NAME: result["name"],
            ReservationDetails.PHONE: result["phone"],
            ReservationDetails.DATE: result["date"],
            ReservationDetails.TIME: result["time"],
            ReservationDetails.GUESTS: str(result["guests"]),
        }
        return f"Found reservation:\n{self.get_reservation_str()}"

    @function_tool()
    async def create_reservation(self, context: RunContext, name: str, phone: str, date: str, time: str, guests: int) -> str:
        logger.info("create reservation - %s, %s, %s, %s, %s", name, phone, date, time, guests)
        result = DB.create_reservation(name, phone, date, time, guests)
        self._reservation = {
            ReservationDetails.NAME: result["name"],
            ReservationDetails.PHONE: result["phone"],
            ReservationDetails.DATE: result["date"],
            ReservationDetails.TIME: result["time"],
            ReservationDetails.GUESTS: str(result["guests"])
        }
        return f"Reservation created:\n{self.get_reservation_str()}"

    @function_tool()
    async def get_reservation_details(self, context: RunContext) -> str:
        logger.info("get reservation details")
        if not self.has_reservation():
            return "No reservation information available."
        return f"Current reservation details:\n{self.get_reservation_str()}"

async def entrypoint(ctx: agents.JobContext):
    model = google.beta.realtime.RealtimeModel(
        instructions=AGENT_INSTRUCTION,
        temperature=0.7,
        voice="Aoede",
    )

    session = AgentSession(llm=model)
    agent = RestaurantAgent()

    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC()
        ),
    )
    await ctx.connect()

    await session.generate_reply(instructions=SESSION_INSTRUCTION)

    @session.on("user_message")
    def on_user(msg):
        import asyncio
        asyncio.create_task(handle_user(msg))

    async def handle_user(msg):
        if agent.has_reservation():
            await session.send_user_message(msg.content)
            await session.generate_reply()
        else:
            await session.send_user_message(msg.content)
            await session.generate_reply(instructions=LOOKUP_RESERVATION_MESSAGE(msg.content))

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))