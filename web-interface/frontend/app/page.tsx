import PasswordGate from "@/components/PasswordGate";
import AvatarPanel from "@/components/AvatarPanel";
import MatrixPanel from "@/components/MatrixPanel";
import CommandDashboard from "@/components/CommandDashboard";

export default function Home() {
  return (
    <PasswordGate>
      <div className="grid grid-rows-2 grid-cols-2 h-screen w-screen overflow-hidden bg-app-bg gap-2 p-2">
        {/* Panel 1: Top-left — Video Avatar */}
        <div className="col-span-1 row-span-1 overflow-hidden rounded-lg border border-app-border bg-app-panel">
          <AvatarPanel />
        </div>

        {/* Panel 2: Top-right — 3D Matrix */}
        <div className="col-span-1 row-span-1 overflow-hidden rounded-lg border border-app-border bg-app-panel">
          <MatrixPanel />
        </div>

        {/* Panel 3: Bottom-full — Dashboard */}
        <div className="col-span-2 row-span-1 overflow-hidden rounded-lg border border-app-border bg-app-panel">
          <CommandDashboard />
        </div>
      </div>
    </PasswordGate>
  );
}
