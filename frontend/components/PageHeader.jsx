export default function PageHeader({ title, children }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <h1 className="text-3xl font-extrabold leading-tight">{title}</h1>
      {children}
    </div>
  );
}
