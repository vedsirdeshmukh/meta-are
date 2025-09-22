// Copyright (c) Meta Platforms, Inc. and affiliates.
// All rights reserved.
//
// This source code is licensed under the terms described in the LICENSE file in
// the root directory of this source tree.

import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import AppWrapper from "../App";
import { NotificationsContext } from "../contexts/NotificationsContextProvider";

vi.mock("../relay/RelayEnvironment");

it("renders Meta Agents Research Environments header", () => {
  render(
    <NotificationsContext.Provider
      value={{ snackPack: [], notify: vi.fn(), clear: vi.fn() }}
    >
      <AppWrapper />
    </NotificationsContext.Provider>,
  );
  const headerElement = screen.findByTestId("server-status");
  expect(headerElement).not.toBeNull();
});
