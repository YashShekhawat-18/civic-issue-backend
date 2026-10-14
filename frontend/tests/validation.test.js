import { describe, expect, it } from "vitest";
import { fieldErrorsFromApi, validateLogin, validateRegister } from "@/lib/validation";

const good = { name: "Asha Rao", email: "asha@example.com", password: "secret123", confirmPassword: "secret123", phone: "" };

describe("validateRegister", () => {
  it("accepts a valid form", () => expect(validateRegister(good)).toEqual({}));
  it("rejects short name, bad email", () => {
    const e = validateRegister({ ...good, name: "A", email: "nope" });
    expect(e.name).toBeTruthy();
    expect(e.email).toBeTruthy();
  });
  it("enforces password rules like the backend", () => {
    expect(validateRegister({ ...good, password: "short1", confirmPassword: "short1" }).password).toMatch(/8/);
    expect(validateRegister({ ...good, password: "onlyletters", confirmPassword: "onlyletters" }).password).toMatch(/number/);
    expect(validateRegister({ ...good, password: "12345678", confirmPassword: "12345678" }).password).toMatch(/letter/);
    const long = "a1".repeat(40);
    expect(validateRegister({ ...good, password: long, confirmPassword: long }).password).toMatch(/72/);
  });
  it("requires matching confirmation", () => {
    expect(validateRegister({ ...good, confirmPassword: "different1" }).confirmPassword).toBeTruthy();
  });
  it("phone is optional but validated when present", () => {
    expect(validateRegister({ ...good, phone: "+919876543210" })).toEqual({});
    expect(validateRegister({ ...good, phone: "12345" }).phone).toBeTruthy();
  });
});

describe("validateLogin", () => {
  it("requires email and password", () => {
    expect(Object.keys(validateLogin({ email: "", password: "" }))).toEqual(["email", "password"]);
    expect(validateLogin({ email: "a@b.co", password: "x" })).toEqual({});
  });
});

describe("fieldErrorsFromApi", () => {
  it("maps first message per field", () => {
    expect(fieldErrorsFromApi([{ field: "email", message: "bad" }, { field: "email", message: "x" }, { field: "name", message: "n" }])).toEqual({ email: "bad", name: "n" });
    expect(fieldErrorsFromApi(undefined)).toEqual({});
  });
});
