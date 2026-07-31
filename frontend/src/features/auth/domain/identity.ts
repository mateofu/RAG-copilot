export type Membership = {
  organizationId: string;
  organizationName: string;
  organizationSlug: string;
  role: "owner" | "editor" | "viewer";
};

export type Identity = {
  userId: string;
  email: string;
  displayName: string;
  memberships: Membership[];
};

export type Credentials = { email: string; password: string };
