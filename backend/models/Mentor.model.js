import mongoose from "mongoose";

const { Schema, model
} = mongoose;

const MentorSchema = new Schema(
  {
    mentorId: {
      type: String,
      required: true,
      unique: true,
      index: true,
      trim: true,
      uppercase: true,
    },
    name: {
       type: String, 
       required: true, 
       trim: true
    },
    // Keep contact as a string: placeholder phone values may contain leading zeros or +.
    contact: { 
      type: String, 
      default: null, 
      trim: true
    },
    email: { 
      type: String, 
      default: null, 
      trim: true, 
      lowercase: true
    },
    linkedin: { 
      type: String, 
      default: null, 
      trim: true
    },
    city: { 
      type: String, 
      default: null, 
      trim: true
    },
    domain: { 
      type: String, 
      default: null, 
      trim: true
    },
    company: { 
      type: String, 
      default: null, 
      trim: true
    },
    masterSector: { 
      type: String, 
      default: null, 
      trim: true
    },
    sectorsOfExpertise: { 
      type: [String], 
      default: []
    },
    rolesOfExpertise: { 
      type: [String], 
      default: []
    },
    seniority: { 
      type: String, 
      default: null, 
      trim: true
    },
    aiProfile: {
      isAINative: { 
        type: Boolean, 
        default: null
      },
      builtAIProductOrWorkflow: { 
        type: Boolean, 
        default: null
      },
      subdomains: { 
        type: [String], 
        default: []
      },
      tools: { 
        type: [String], 
        default: []
      },
    },
    toolExperience: {
      tableau: { 
        type: Boolean, 
        default: null
      },
      hubspot: { 
        type: Boolean, 
        default: null
      },
      googleAnalytics: { 
        type: Boolean, 
        default: null
      },
      jira: { 
        type: Boolean, 
        default: null
      },
      excel: { 
        type: Boolean, 
        default: null
      },
      mixpanel: { 
        type: Boolean, 
        default: null
      },
    },
    mentorshipQuality: {
      type: String,
      enum: [
      "Excellent",
      "Good",
      "Average",
      "Poor",
      null
      ],
      default: null,
    },
    activitiesParticipated: { 
      type: Number, 
      min: 0, 
      default: null
    },
    dataQualityIssues: { 
      type: [String], 
      default: []
    },
  },
  { timestamps: true, versionKey: false},
);

export default model("Mentor", MentorSchema);
