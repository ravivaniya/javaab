interface Props {
  children: React.ReactNode;
}

/** No-op guard — widget is open (no student auth). Kept for JSX compatibility. */
export function RequireAuth({ children }: Props) {
  return <>{children}</>;
}
