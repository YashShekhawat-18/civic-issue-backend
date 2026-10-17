import RoadTracker from "./RoadTracker";

// Two-column layout for login and register: a short pitch on the left, the form on the right.
export default function AuthShell({ children }) {
  return (
    <div className="mx-auto grid max-w-4xl overflow-hidden rounded-3xl border border-line bg-white shadow-sm md:grid-cols-5">
      <aside className="hidden bg-asphalt p-8 text-white md:col-span-2 md:flex md:flex-col md:justify-between">
        <div>
          <h2 className="text-3xl font-extrabold leading-tight">Fix your street, together.</h2>
          <p className="mt-3 text-white/75">
            Report a problem with a photo and a pin. Follow it from the first report to the day it is fixed.
          </p>
        </div>
        <div className="mt-10 rounded-2xl bg-white p-4 pt-5 text-asphalt">
          <RoadTracker status="IN_PROGRESS" compact />
          <p className="mt-3 text-center text-xs text-asphalt-soft">Every complaint is tracked like this.</p>
        </div>
      </aside>
      <div className="p-6 sm:p-8 md:col-span-3">{children}</div>
    </div>
  );
}
