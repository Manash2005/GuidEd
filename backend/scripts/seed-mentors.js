import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import dotenv from "dotenv";
import mongoose from "mongoose";
import Mentor from "../models/Mentor.model.js";

const dataPath = fileURLToPath(new URL("../data/mentors.json", import.meta.url));
const envPath = fileURLToPath(new URL("../.env", import.meta.url));

dotenv.config({ path: envPath });

const mongoUri = process.env.MONGODB_URI;
if (!mongoUri) {
  throw new Error(`MONGODB_URI is not set in ${envPath}`);
}

const mentors = JSON.parse(await readFile(dataPath, "utf8"));
if (!Array.isArray(mentors)) {
  throw new TypeError(`${dataPath} must contain a JSON array`);
}

const mentorIds = new Set();
for (const [index, mentor] of mentors.entries()) {
  if (!mentor.mentorId || !mentor.name) {
    throw new Error(`Mentor at index ${index} is missing mentorId or name`);
  }
  if (mentorIds.has(mentor.mentorId)) {
    throw new Error(`Duplicate mentorId in source data: ${mentor.mentorId}`);
  }
  mentorIds.add(mentor.mentorId);
  await new Mentor(mentor).validate();
}

try {
  await mongoose.connect(mongoUri);
  const result = await Mentor.bulkWrite(
    mentors.map((mentor) => ({
      updateOne: {
        filter: { mentorId: mentor.mentorId },
        update: { $set: mentor },
        upsert: true,
      },
    })),
  );

  console.log(
    `Imported ${mentors.length} mentors (${result.upsertedCount} inserted, ${result.modifiedCount} updated).`,
  );
} finally {
  await mongoose.disconnect();
}
